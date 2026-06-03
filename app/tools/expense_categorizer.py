"""
Categorize transactions by merchant patterns.

Rule-based keyword matching - reliable, deterministic, fast (no LLM needed
for this step). The LLM-powered agents then interpret these categorized
totals semantically.
"""

from collections import defaultdict

# Category -> list of substring patterns (matched case-insensitively)
CATEGORY_PATTERNS = {
    "Salary":          ["SALARY CREDIT", "SALARY TRANSFER"],
    "Bonus":           ["EID AL FITR BONUS", "EID BONUS", "ANNUAL BONUS"],
    "Rent":            ["RENT CHEQUE", "RENT TRANSFER", "RENT PAYMENT"],
    "Mortgage":        ["HOME LOAN INSTALLMENT", "MORTGAGE"],
    "Car Loan":        ["CAR FINANCE INSTALLMENT", "AUTO LOAN", "CAR LOAN"],
    "Utilities":       ["DEWA", "SEWA", "ADDC"],
    "Telecom":         ["ETISALAT", "DU TELECOM"],
    "Insurance":       ["INSURANCE", "DAMAN HEALTH", "ORIENT INSURANCE", "AXA"],
    "Education":       ["NURSERY", "SCHOOL FEE", "TERM FEE", "GEMS", "ACADEMY",
                        "STEPPING STONES", "EARLY LEARNING"],
    "Groceries":       ["CARREFOUR HYPER", "CARREFOUR ONLINE", "LULU", "SPINNEYS",
                        "UNION COOP", "CHOITHRAMS", "WEST ZONE", "GEANT", "ZOOM"],
    "Food Delivery":   ["TALABAT", "DELIVEROO", "CAREEM NOW", "ZOMATO", "SMILES BY"],
    "Dining Out":      ["TEXAS ROADHOUSE", "PF CHANGS", "OPERATION FALAFEL",
                        "AL FANAR", "AUTOMATIC", "MCDONALDS", "KFC", "PIZZA HUT",
                        "FIVE GUYS", "SHAKE SHACK", "CAFE BATEEL", "ALLO BEIRUT",
                        "ZAROOB", "KARAK"],
    "Coffee":          ["STARBUCKS", "COSTA COFFEE", "TIM HORTONS", "CAFE NERO"],
    "Fuel":            ["ADNOC", "ENOC", "EPPCO"],
    "Salik (Tolls)":   ["SALIK"],
    "Transport":       ["CAREEM NETWORK", "UBER B.V.", "PARKIN", "MERAAS PARKING",
                        "RTA NOL", "RTA METRO", "RTA BUS"],
    "Online Shopping": ["AMAZON.AE", "NOON.COM", "SHARAF DG", "NAMSHI", "FIRSTCRY",
                        "OUNASS"],
    "Clothing":        ["H AND M", "ZARA ", "ZARA KIDS", "UNIQLO", "SPLASH",
                        "MAX FASHION", "MARKS AND SPENCER", "MOTHERCARE",
                        "CENTREPOINT", "BABYSHOP", "BLOOMINGDALES"],
    "Pharmacy":        ["ASTER PHARMACY", "LIFE PHARMACY", "BIN SINA", "BOOTS PHARMACY"],
    "Healthcare":      ["MEDICLINIC", "NMC ROYAL", "AMERICAN HOSPITAL",
                        "EMIRATES HOSPITAL"],
    "Subscriptions":   ["NETFLIX", "SPOTIFY", "DISNEY", "AMAZON PRIME", "OSN",
                        "APPLE.COM", "APPLE ICLOUD", "ICLOUD STORAGE", "LINKEDIN PREMIUM",
                        "ANGHAMI", "MICROSOFT*365", "GOOGLE *YOUTUBE",
                        "NOON.COM VIP"],
    "Entertainment":   ["VOX CINEMAS", "REEL CINEMAS", "IMG WORLDS", "GLOBAL VILLAGE",
                        "KIDZANIA", "PLAY CITY", "TOYS R US"],
    "Travel":          ["FLYDUBAI", "EMIRATES AIRLINES", "BOOKING.COM", "BOLT ",
                        "SAUDI AIRLINES"],
    "Gold / Jewelry":  ["JOYALUKKAS", "DAMAS JEWELLERY", "MALABAR GOLD"],
    "Remittance":      ["AL ANSARI EXCHANGE", "UAE EXCHANGE", "WISE PAYMENTS",
                        "LULU EXCHANGE", "REMITTANCE"],
    "Charity":         ["RED CRESCENT", "DUBAI CARES", "DONATION", "ZAKAT"],
    "ATM Cash":        ["ATM CASH WITHDRAWAL"],
    "Card Payment":    ["CREDIT CARD AUTOPAY", "CREDIT CARD SETTLEMENT",
                        "PAYMENT RECEIVED"],
    "Savings Transfer":["TRANSFER TO ADCB ACTIVE SAVER", "TRANSFER TO FAB SMART",
                        "WAKALA INVESTMENT", "GOALS SAVER"],
    "Home / Furniture":["IKEA", "HOME CENTRE", "PAN EMIRATES", "ACE HARDWARE"],
}

# Categories that count as DISCRETIONARY (candidates for cuts)
DISCRETIONARY = {
    "Food Delivery", "Dining Out", "Coffee", "Online Shopping", "Clothing",
    "Subscriptions", "Entertainment", "Travel", "Gold / Jewelry",
}

# Categories that count as FIXED / essential
FIXED = {
    "Rent", "Mortgage", "Car Loan", "Utilities", "Telecom", "Insurance",
    "Education",
}


def categorize_one(description: str) -> str:
    """Match a single transaction description to a category."""
    up = description.upper()
    for category, patterns in CATEGORY_PATTERNS.items():
        for pat in patterns:
            if pat in up:
                return category
    return "Other"


def categorize_transactions(transactions: list[dict]) -> list[dict]:
    """Add 'category' field to each transaction. Returns the same list (mutated)."""
    for tx in transactions:
        tx["category"] = categorize_one(tx["description"])
    return transactions


def aggregate_by_category(transactions: list[dict],
                          months: float) -> dict[str, dict]:
    """
    Build per-category totals + monthly averages.

    Returns {category: {total: X, count: N, avg_per_month: M}}
    Only debit transactions are counted (i.e. money spent).
    """
    totals = defaultdict(float)
    counts = defaultdict(int)
    for tx in transactions:
        if tx["kind"] != "debit":
            continue
        cat = tx.get("category") or categorize_one(tx["description"])
        totals[cat] += tx["amount"]
        counts[cat] += 1
    return {
        cat: {
            "total": round(totals[cat], 2),
            "count": counts[cat],
            "avg_per_month": round(totals[cat] / months, 2),
        }
        for cat in sorted(totals, key=lambda c: -totals[c])
    }


def split_fixed_vs_variable(by_category: dict[str, dict]) -> tuple[float, float, float]:
    """
    Returns (monthly_fixed, monthly_variable, monthly_discretionary).

    Fixed = housing, utilities, telecom, insurance, education, loans
    Discretionary = leisure/lifestyle (subset of variable)
    Variable = everything else not income-related
    """
    fixed = 0.0
    discretionary = 0.0
    other_variable = 0.0
    ignore = {"Salary", "Bonus", "Card Payment", "Savings Transfer", "ATM Cash"}
    for cat, stats in by_category.items():
        if cat in ignore:
            continue
        avg = stats["avg_per_month"]
        if cat in FIXED:
            fixed += avg
        elif cat in DISCRETIONARY:
            discretionary += avg
        else:
            other_variable += avg
    return round(fixed, 2), round(other_variable + discretionary, 2), round(discretionary, 2)
