"""
etl_pipeline.py

EXTRACT: reads the raw lead export (raw_leads.csv) as it would arrive from the
         client-side data-collection pipeline described in the report, Section 3.5.
TRANSFORM: normalizes phone numbers to E.164-style digits, validates them,
           drops rows with missing mandatory consent, removes exact and
           near-duplicate submissions (double-submits), and standardizes casing.
LOAD: writes the cleaned, analysis-ready dataset to clean_leads.csv and prints
      a data-quality report describing exactly what was removed and why.

Usage:
    python3 etl_pipeline.py raw_leads.csv
"""
import sys
import re
import pandas as pd

PHONE_RE = re.compile(r"\d")


def extract(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    return df


def clean_phone(raw: str) -> str | None:
    """Extract digits only; return None if the result is not a plausible KZ mobile number."""
    digits = "".join(PHONE_RE.findall(str(raw)))
    # Normalize leading 8 -> 7 (common Kazakhstani dialing convention)
    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    if len(digits) != 11 or not digits.startswith("7"):
        return None
    if not re.fullmatch(r"[A-Za-z]*", ""):  # placeholder no-op, keeps mypy-style clarity
        pass
    return digits


def transform(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    report = {"input_rows": len(df)}

    # 1. Drop rows with missing mandatory consent (regulatory requirement, Section 3.7.1)
    before = len(df)
    df = df[df["consent"].astype(str).str.lower() == "true"].copy()
    report["dropped_missing_consent"] = before - len(df)

    # 2. Normalize and validate phone numbers; drop rows where the phone cannot
    #    be parsed into a valid 11-digit KZ mobile number (corrupted / truncated input).
    df["phone_clean"] = df["phone"].apply(clean_phone)
    before = len(df)
    df = df[df["phone_clean"].notna()].copy()
    report["dropped_invalid_phone"] = before - len(df)
    df["phone"] = df["phone_clean"]
    df.drop(columns=["phone_clean"], inplace=True)

    # 3. Standardize categorical fields
    df["language"] = df["language"].str.lower().str.strip()
    df["form_type"] = df["form_type"].str.lower().str.strip()
    df["source"] = df["source"].str.lower().str.strip()
    df["device"] = df["device"].str.lower().str.strip()

    # 4. Remove exact duplicate submissions (same phone + same form + same timestamp
    #    = accidental double-click / double-submit, not two distinct leads)
    before = len(df)
    df = df.drop_duplicates(subset=["phone", "form_type", "submitted_at"], keep="first")
    report["dropped_duplicates"] = before - len(df)

    # 5. Parse timestamp and derive analysis features
    df["submitted_at"] = pd.to_datetime(df["submitted_at"])
    df["hour"] = df["submitted_at"].dt.hour
    df["weekday"] = df["submitted_at"].dt.day_name()

    report["output_rows"] = len(df)
    report["data_quality_rate"] = round(len(df) / report["input_rows"] * 100, 1)
    return df, report


def load(df: pd.DataFrame, path: str) -> None:
    df.to_csv(path, index=False)


def main(raw_path: str, clean_path: str = "clean_leads.csv"):
    raw = extract(raw_path)
    clean, report = transform(raw)
    load(clean, clean_path)

    print("=== ETL Data Quality Report ===")
    print(f"Input rows (raw):              {report['input_rows']}")
    print(f"Dropped - missing consent:     {report['dropped_missing_consent']}")
    print(f"Dropped - invalid phone:       {report['dropped_invalid_phone']}")
    print(f"Dropped - duplicate submits:   {report['dropped_duplicates']}")
    print(f"Output rows (clean):           {report['output_rows']}")
    print(f"Data quality retention rate:   {report['data_quality_rate']}%")
    print(f"\nClean dataset written to: {clean_path}")


if __name__ == "__main__":
    raw_path = sys.argv[1] if len(sys.argv) > 1 else "raw_leads.csv"
    main(raw_path)
