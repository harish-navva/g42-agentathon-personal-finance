"""
UAE-specific knowledge module.

Contains constants and helper functions for UAE personal finance context:
- Rent cheque cycles (when rent payments hit)
- Salary timing
- Eid bonus timing
- Sharia-compliant investment options
- End-of-Service-Benefits (EOSB) rules
- DEWA/Salik/Etisalat patterns
"""

from datetime import date

# Recommended emergency fund as months of essential expenses
EMERGENCY_FUND_TARGET_MONTHS = (3, 6)

# UAE rent cheque cycles (number of cheques per year)
COMMON_RENT_CHEQUES = [1, 2, 4, 6, 12]

# Sharia-compliant investment products available in UAE
SHARIA_INVESTMENT_OPTIONS = [
    {"name": "DIB Sukuk", "type": "fixed_income", "risk": "low",
     "min_aed": 5000, "expected_return_pct": (3.5, 5.0)},
    {"name": "Wahed Invest (halal robo)", "type": "diversified", "risk": "medium",
     "min_aed": 500, "expected_return_pct": (5.0, 8.0)},
    {"name": "FAB Islamic Equity Fund", "type": "equity", "risk": "medium-high",
     "min_aed": 10000, "expected_return_pct": (6.0, 10.0)},
    {"name": "Gold (physical or digital)", "type": "commodity", "risk": "medium",
     "min_aed": 500, "expected_return_pct": (4.0, 8.0)},
]

CONVENTIONAL_INVESTMENT_OPTIONS = [
    {"name": "Sarwa diversified portfolio", "type": "diversified", "risk": "medium",
     "min_aed": 500, "expected_return_pct": (6.0, 9.0)},
    {"name": "Stake (UAE real estate)", "type": "real_estate", "risk": "medium",
     "min_aed": 500, "expected_return_pct": (5.0, 10.0)},
    {"name": "ADCB Active Saver", "type": "savings", "risk": "very low",
     "min_aed": 0, "expected_return_pct": (1.5, 3.0)},
    {"name": "Vanguard ETFs via UAE broker", "type": "equity", "risk": "medium-high",
     "min_aed": 1000, "expected_return_pct": (7.0, 11.0)},
]


# UAE seasonal cashflow notes
RENT_CHEQUE_MONTHS_QUARTERLY = [9, 12, 3, 6]  # if 4-cheque cycle from Sept lease
EID_AL_FITR_2026 = date(2026, 4, 1)            # approximate
EID_AL_ADHA_2026 = date(2026, 6, 8)            # approximate
RAMADAN_START_2026 = date(2026, 2, 18)
BACK_TO_SCHOOL_MONTH = 9                       # Sept


def is_rent_cheque_month(month: int, cycle: list[int] = None) -> bool:
    """True if the given month is a rent-cheque month for this user."""
    cycle = cycle or RENT_CHEQUE_MONTHS_QUARTERLY
    return month in cycle


def best_vacation_month(rent_cheque_months: list[int],
                        bonus_month: int = 4,
                        school_year_start_month: int = 9) -> dict:
    """
    Suggest the best vacation month based on cashflow patterns.

    Best months are those that are:
    - NOT a rent-cheque month
    - NOT back-to-school (Sep)
    - PREFERABLY right after Eid bonus (April-May) or before summer (May)
    - Avoiding Ramadan if applicable (Feb-Mar 2026)
    """
    # Score each month
    scores = {}
    for m in range(1, 13):
        score = 100
        if m in rent_cheque_months:
            score -= 50
        if m == school_year_start_month:
            score -= 30
        if m == bonus_month + 1:  # month after Eid bonus arrives
            score += 30
        if m in (5, 11):  # mild weather + low season
            score += 15
        if m in (7, 8):    # summer heat (still good for travel since you leave UAE!)
            score += 5
        if m in (2, 3):    # Ramadan
            score -= 10
        scores[m] = score

    sorted_months = sorted(scores.items(), key=lambda x: -x[1])
    month_names = ["Jan","Feb","Mar","Apr","May","Jun",
                   "Jul","Aug","Sep","Oct","Nov","Dec"]
    return {
        "best_month": month_names[sorted_months[0][0] - 1],
        "best_month_num": sorted_months[0][0],
        "reasoning": (
            f"{month_names[sorted_months[0][0]-1]} avoids rent-cheque months and "
            f"benefits from the Eid bonus arriving in April."
        ),
        "ranked": [(month_names[m-1], s) for m, s in sorted_months[:6]],
    }


def estimate_vacation_budget(
    family_size: int,
    destination_tier: str = "mid",  # "budget" | "mid" | "premium"
    duration_days: int = 5,
) -> dict:
    """Rough vacation budget estimate for a UAE family."""
    # Per-person daily rates (AED)
    rates = {
        "budget":  {"flight": 800, "hotel_per_night": 250, "food": 120, "activities": 80},
        "mid":     {"flight": 1500, "hotel_per_night": 450, "food": 200, "activities": 150},
        "premium": {"flight": 3000, "hotel_per_night": 900, "food": 350, "activities": 300},
    }
    r = rates.get(destination_tier, rates["mid"])

    # Hotel is usually 1 room per family (not per person)
    flight = r["flight"] * family_size
    hotel = r["hotel_per_night"] * duration_days
    food = r["food"] * family_size * duration_days
    activities = r["activities"] * family_size * duration_days
    total = flight + hotel + food + activities

    return {
        "flight": round(flight),
        "hotel": round(hotel),
        "food": round(food),
        "activities": round(activities),
        "total_aed": round(total),
        "destination_examples": {
            "budget":  ["Georgia (Tbilisi)", "Egypt", "Sri Lanka", "Azerbaijan"],
            "mid":     ["Turkey", "Thailand", "Salalah (UAE)", "Malaysia"],
            "premium": ["Maldives", "Switzerland", "Singapore", "Italy"],
        }[destination_tier],
    }


def required_disclaimer() -> str:
    """The mandatory financial advice disclaimer."""
    return (
        "⚠️  This guidance is generated by an AI agent system based on the user's "
        "transaction patterns. It is NOT financial advice. Investment products "
        "involve risk including possible loss of principal. Past patterns do not "
        "guarantee future income. Consult a qualified financial advisor licensed "
        "by the SCA (UAE Securities & Commodities Authority) before making major "
        "financial decisions."
    )
