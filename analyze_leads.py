"""
analyze_leads.py

Runs on the CLEAN dataset produced by etl_pipeline.py (clean_leads.csv).

1. Descriptive statistics: language split, source/device breakdown.
2. Inferential statistics: a chi-square test of independence between
   interface language (RU/KZ) and which form a visitor used, plus a
   Wilson confidence interval for the KZ-language submission share.
3. A simple predictive model: logistic regression predicting whether a
   visitor will use the quick hero form vs. the longer contact form,
   based on device, source, and time spent on page.
4. A summary chart (language split + form-type split).

Usage:
    python3 analyze_leads.py clean_leads.csv
"""
import sys
import math
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import chi2_contingency
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline


def wilson_ci(successes: int, n: int, z: float = 1.96):
    """Wilson score confidence interval for a binomial proportion."""
    p_hat = successes / n
    denom = 1 + z**2 / n
    centre = p_hat + z**2 / (2 * n)
    margin = z * math.sqrt((p_hat * (1 - p_hat) + z**2 / (4 * n)) / n)
    lower = (centre - margin) / denom
    upper = (centre + margin) / denom
    return p_hat, lower, upper


def main(path):
    df = pd.read_csv(path, parse_dates=["submitted_at"])
    n = len(df)
    print(f"Clean leads analyzed: {n}\n")

    lang_counts = df["language"].value_counts()
    form_counts = df["form_type"].value_counts()
    print("Language split:\n" + lang_counts.to_string())
    print("\nForm-type split:\n" + form_counts.to_string())
    print("\nTraffic source split:\n" + df["source"].value_counts().to_string())

    contingency = pd.crosstab(df["language"], df["form_type"])
    chi2, p_value, dof, expected = chi2_contingency(contingency)
    print("\n=== Chi-square test: is form choice independent of interface language? ===")
    print(contingency)
    print(f"chi2 = {chi2:.3f}, dof = {dof}, p-value = {p_value:.3f}")
    if p_value < 0.05:
        print("=> Statistically significant association (p < 0.05): language and form choice are NOT independent.")
    else:
        print("=> No statistically significant association (p >= 0.05): consistent with language and "
              "form choice being independent in this sample.")

    kz_n = int((df["language"] == "kz").sum())
    p_hat, lo, hi = wilson_ci(kz_n, n)
    print(f"\nKZ-language share: {p_hat:.1%} (95% Wilson CI: {lo:.1%} - {hi:.1%}), n={n}")

    model_df = df.copy()
    model_df["target"] = (model_df["form_type"] == "hero_quick_form").astype(int)
    features = ["device", "source", "time_on_page_sec"]
    X = model_df[features]
    y = model_df["target"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y if y.nunique() > 1 else None
    )

    pre = ColumnTransformer(
        transformers=[("cat", OneHotEncoder(handle_unknown="ignore"), ["device", "source"])],
        remainder="passthrough",
    )
    clf = Pipeline([("pre", pre), ("logreg", LogisticRegression(max_iter=1000))])
    clf.fit(X_train, y_train)
    preds = clf.predict(X_test)
    acc = accuracy_score(y_test, preds)

    print("\n=== Predictive model: P(visitor uses the quick hero form) ===")
    print("Features: device, traffic source, time on page (seconds)")
    print(f"Train/test split: {len(X_train)}/{len(X_test)} rows")
    print(f"Test accuracy: {acc:.1%}")
    print("\nClassification report:")
    print(classification_report(y_test, preds, target_names=["contact_form", "hero_quick_form"], zero_division=0))

    fig, axes = plt.subplots(1, 2, figsize=(9, 4))
    lang_counts.plot(kind="bar", ax=axes[0], color=["#1B2A4A", "#C9A227"])
    axes[0].set_title("Clean leads by interface language")
    axes[0].tick_params(axis="x", rotation=0)
    form_counts.plot(kind="bar", ax=axes[1], color=["#1B2A4A", "#8B93A1"])
    axes[1].set_title("Clean leads by form type")
    axes[1].tick_params(axis="x", rotation=15)
    plt.tight_layout()
    plt.savefig("leads_analysis.png", dpi=150)
    print("\nChart saved to leads_analysis.png")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "clean_leads.csv"
    main(path)
