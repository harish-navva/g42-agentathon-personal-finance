"""
Pure-Python math for savings-goal questions. No LLM needed.

The agents use these calculations to ground their reasoning in real numbers,
not hallucinated guesses.
"""

import re
from dataclasses import dataclass


@dataclass
class GoalResult:
    feasible: bool
    target_amount: float
    months_available: int
    current_monthly_savings: float
    required_monthly_savings: float
    shortfall_per_month: float
    shortfall_total: float
    feasible_after_cuts_monthly: float
    options: list[dict]


def extract_amount_and_timeline(query: str) -> tuple[float | None, int | None]:
    """
    Best-effort regex extraction of (amount_aed, months).

    Examples:
        "Can I buy a 60K car in 3 months?"     -> (60000, 3)
        "Save 100,000 AED in 12 months"        -> (100000, 12)
        "buy a 45000 AED car next year"        -> (45000, 12)
    """
    q = query.upper().replace(",", "")

    # Amount: number optionally followed by K or AED
    amount = None
    m = re.search(r"(\d+(?:\.\d+)?)\s*K(?!\w)", q)
    if m:
        amount = float(m.group(1)) * 1000
    else:
        m = re.search(r"(\d{3,7})\s*(?:AED|DIRHAM)?", q)
        if m:
            amount = float(m.group(1))

    # Timeline
    months = None
    m = re.search(r"(\d+)\s*MONTH", q)
    if m:
        months = int(m.group(1))
    elif "YEAR" in q:
        m = re.search(r"(\d+)\s*YEAR", q)
        months = (int(m.group(1)) if m else 1) * 12
    elif "NEXT YEAR" in q:
        months = 12

    return amount, months


def compute_goal_feasibility(
    target_amount: float,
    months: int,
    current_monthly_savings: float,
    current_buffer: float,
    discretionary_spend_monthly: float,
    keep_emergency_months: float = 3.0,
    monthly_essential_costs: float = 17000.0,
) -> GoalResult:
    """
    Compute whether the goal is feasible and what cuts would help.

    Args:
        target_amount: e.g. 60000 (AED)
        months: e.g. 3
        current_monthly_savings: avg savings/month from current spending
        current_buffer: AED currently in savings account
        discretionary_spend_monthly: total discretionary spend that could be cut
        keep_emergency_months: minimum emergency fund to preserve
        monthly_essential_costs: used to compute emergency fund floor
    """
    emergency_floor = keep_emergency_months * monthly_essential_costs
    usable_buffer = max(0.0, current_buffer - emergency_floor)

    required_total = target_amount
    required_monthly = (required_total - usable_buffer) / months
    shortfall_monthly = max(0.0, required_monthly - current_monthly_savings)
    shortfall_total = max(0.0, required_total - usable_buffer - current_monthly_savings * months)

    # Assume realistic cuts = 50% of discretionary spend
    realistic_cuts_monthly = discretionary_spend_monthly * 0.5
    feasible_after_cuts = current_monthly_savings + realistic_cuts_monthly
    feasible_with_cuts = (feasible_after_cuts * months + usable_buffer) >= required_total

    feasible = current_monthly_savings * months + usable_buffer >= required_total

    # Build options
    options = []

    # Option A: extend timeline
    if not feasible:
        months_needed = (required_total - usable_buffer) / max(current_monthly_savings, 1e-3)
        options.append({
            "label": "Extend timeline",
            "description": (
                f"At your current savings rate of AED {current_monthly_savings:,.0f}/month, "
                f"you'd reach AED {target_amount:,.0f} in about {months_needed:.0f} months."
            ),
            "months": round(months_needed, 1),
            "feasible": True,
        })

    # Option B: aggressive cuts
    options.append({
        "label": "Cut discretionary by 50%",
        "description": (
            f"Reducing dining-out / subscriptions / shopping by ~50% frees up "
            f"AED {realistic_cuts_monthly:,.0f}/month. Combined with your existing "
            f"savings, you'd save AED {feasible_after_cuts:,.0f}/month."
        ),
        "additional_savings": round(realistic_cuts_monthly, 0),
        "feasible_in_timeline": feasible_with_cuts,
    })

    # Option C: partial down payment + finance
    down_payment_pct = 0.4
    down_payment = target_amount * down_payment_pct
    financed_amount = target_amount - down_payment
    # 4-year financing at ~5% effective rate (rough estimate)
    monthly_emi = (financed_amount * 1.10) / 48
    if usable_buffer >= down_payment * 0.7 or feasible_with_cuts:
        options.append({
            "label": f"Pay {int(down_payment_pct*100)}% down, finance the rest",
            "description": (
                f"AED {down_payment:,.0f} down payment + AED {financed_amount:,.0f} financed "
                f"over 4 years ≈ AED {monthly_emi:,.0f}/month EMI. Preserves your emergency fund."
            ),
            "down_payment": round(down_payment, 0),
            "monthly_emi": round(monthly_emi, 0),
            "feasible": True,
        })

    # Option D: smaller target
    affordable = current_monthly_savings * months + usable_buffer
    if not feasible and affordable >= target_amount * 0.5:
        options.append({
            "label": "Buy a smaller / cheaper option",
            "description": (
                f"At your current pace, AED {affordable:,.0f} is achievable in {months} months. "
                f"A used car or smaller new car in that budget keeps you debt-free."
            ),
            "affordable_amount": round(affordable, 0),
            "feasible": True,
        })

    # Recommended
    recommended = None
    if feasible:
        recommended = "You can afford this at your current savings rate."
    elif any(o.get("label", "").startswith("Pay") for o in options):
        recommended = next(o["label"] for o in options if o["label"].startswith("Pay"))
    elif options:
        recommended = options[0]["label"]

    return GoalResult(
        feasible=feasible,
        target_amount=target_amount,
        months_available=months,
        current_monthly_savings=current_monthly_savings,
        required_monthly_savings=required_monthly,
        shortfall_per_month=round(shortfall_monthly, 2),
        shortfall_total=round(shortfall_total, 2),
        feasible_after_cuts_monthly=round(feasible_after_cuts, 2),
        options=options,
    )
