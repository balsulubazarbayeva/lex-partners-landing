"""
generate_raw_data.py

Simulates a RAW export of lead-form submissions as they would arrive from the
client-side pipeline before any server-side cleaning: duplicate double-submits,
malformed phone numbers, inconsistent casing, and a few missing consent values.
This raw file is the input to etl_pipeline.py.
"""
import csv
import random
import datetime

random.seed(7)

sources = ["organic", "organic", "organic", "instagram", "google_ads", "referral", "direct"]
devices = ["mobile", "mobile", "mobile", "desktop", "tablet"]
langs = ["ru", "ru", "ru", "kz", "kz"]
forms = ["hero_quick_form", "contact_form"]
names_ru = ["Асхат", "Мадина", "Ерлан", "Динара", "Тимур", "Аружан", "Нурлан",
            "Сая", "Бекзат", "Айгерим", "Дамир", "Гульнара", "Санжар", "Алина", "Ержан"]
names_kz = ["Ақбота", "Дәулет", "Мөлдір", "Нұрсұлтан", "Аяулым", "Бақыт", "Жанар", "Серік"]
services = ["business_registration", "contract_law", "labor_disputes", "family_law",
            "tax_consulting", "court_representation", "debt_recovery", "subscription", ""]

def random_phone(dirty=False):
    core = "7717" + str(random.randint(1000000, 9999999))
    if not dirty:
        return core
    variant = random.choice(["spaced", "dashed", "short", "letters", "plus"])
    if variant == "spaced":
        return f"+7 717 {core[4:7]} {core[7:9]} {core[9:11]}"
    if variant == "dashed":
        return f"8-717-{core[4:7]}-{core[7:9]}-{core[9:11]}"
    if variant == "short":
        return core[:6]  # truncated / incomplete number
    if variant == "letters":
        return core[:5] + "abc" + core[8:]  # corrupted input
    return "+" + core

rows = []
start = datetime.datetime(2026, 6, 15, 8, 0)
n = 80
for i in range(n):
    lang = random.choice(langs)
    name = random.choice(names_kz if lang == "kz" else names_ru)
    dirty = random.random() < 0.30
    phone = random_phone(dirty)
    form_type = random.choice(forms)
    source = random.choice(sources)
    device = random.choice(devices)
    service = random.choice(services)
    consent = "" if random.random() < 0.08 else "true"   # ~8% missing consent (should be dropped)
    ts = start + datetime.timedelta(hours=random.randint(0, 470), minutes=random.choice([0, 15, 30, 45]))
    time_on_page_sec = max(4, int(random.gauss(95, 45)))  # time spent before converting
    rows.append([name, phone, lang, form_type, source, device, service, consent, ts.isoformat(), time_on_page_sec])

# Inject ~10% exact duplicate rows (simulating accidental double-submits / double-click)
dupes = random.sample(rows, k=int(n * 0.10))
rows.extend(dupes)
random.shuffle(rows)

with open("raw_leads.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["name", "phone", "language", "form_type", "source", "device",
                "service", "consent", "submitted_at", "time_on_page_sec"])
    w.writerows(rows)

print(f"Generated {len(rows)} raw rows (incl. {len(dupes)} injected duplicates) -> raw_leads.csv")
