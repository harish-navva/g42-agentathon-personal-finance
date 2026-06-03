"""
CrewAI Task definitions.

In our architecture, tasks are issued by the orchestrator dynamically based
on the user query type and on critique events from the blackboard. We don't
pre-build a static task graph here — that would be a linear pipeline and the
hackathon rubric punishes that pattern. Instead, this module exposes helpers
that build a Task for a given agent + context on demand.
"""

from typing import Any


def build_analysis_prompt(query: str, financial_summary: dict) -> str:
    """Prompt for Expense Analyzer — interpret pre-computed totals."""
    return f"""
The user asks: "{query}"

You have access to their pre-categorized spending. Here is the summary:
- Monthly income: AED {financial_summary['monthly_income_aed']:,.0f}
- Monthly fixed costs: AED {financial_summary['monthly_fixed_costs_aed']:,.0f}
- Monthly variable spend: AED {financial_summary['monthly_variable_costs_aed']:,.0f}
- Monthly net savings: AED {financial_summary['monthly_savings_aed']:,.0f} ({financial_summary['savings_rate_pct']:.1f}%)
- Current buffer: AED {financial_summary['current_buffer_aed']:,.0f} ({financial_summary['buffer_months']:.1f} months of expenses)

Top spending categories (avg/month):
{_format_categories(financial_summary.get('by_category', {}))}

In 3-5 sentences, write a plain-English interpretation of where this person's
money is going. Identify the SINGLE biggest opportunity to cut spending without
hurting essential needs. Be specific with AED amounts.
""".strip()


def build_risk_assessment_prompt(financial_summary: dict, user_profile: dict) -> str:
    """Prompt for Risk Profiler."""
    return f"""
Build a risk tolerance assessment for this UAE expat:

Profile:
- Age: {user_profile.get('age')}
- Marital status: {user_profile.get('marital_status')}, {user_profile.get('dependents')} dependent(s)
- Residency: {user_profile.get('residency_status')}
- Employment tenure: {user_profile.get('employment', {}).get('tenure_years')} years (private sector)
- Monthly salary: AED {user_profile.get('employment', {}).get('monthly_salary_aed'):,}

Financial position:
- Net monthly savings: AED {financial_summary['monthly_savings_aed']:,.0f} ({financial_summary['savings_rate_pct']:.1f}%)
- Emergency buffer: AED {financial_summary['current_buffer_aed']:,.0f} ({financial_summary['buffer_months']:.1f} months)

Output:
1. Risk band (conservative / moderate / aggressive) with a 0-100 score
2. 3 specific red flags or risks the user should be aware of (one of these
   MUST relate to expat visa-runway risk)
3. The minimum emergency fund this family should maintain in AED
""".strip()


def build_goal_plan_prompt(query: str, goal_math: dict,
                            financial_summary: dict,
                            risk_profile: dict) -> str:
    """Prompt for Goal Planner."""
    feas = "is feasible" if goal_math.get("feasible") else "is NOT feasible at current pace"
    return f"""
The user asks: "{query}"

Goal math (computed, do not recompute):
- Target: AED {goal_math.get('target_amount', 0):,.0f}
- Timeline: {goal_math.get('months_available', 0)} months
- Current monthly savings: AED {goal_math.get('current_monthly_savings', 0):,.0f}
- Required monthly savings: AED {goal_math.get('required_monthly_savings', 0):,.0f}
- Goal {feas}.

Risk profile: {risk_profile.get('band')} ({risk_profile.get('score')}/100)

Pre-computed options:
{_format_options(goal_math.get('options', []))}

Write a coach-style plan in 4-6 sentences. Pick ONE recommended option from
those above. Explain trade-offs in plain language. Do NOT invent numbers
beyond what's provided.
""".strip()


def build_critique_prompt(plan_text: str, financial_summary: dict,
                          risk_profile: dict) -> str:
    """Prompt for Risk Profiler when reviewing the proposed plan."""
    return f"""
Review this plan from the Goal Planner and CRITIQUE it:

PLAN:
{plan_text}

User's financial reality:
- Buffer: AED {financial_summary['current_buffer_aed']:,.0f} ({financial_summary['buffer_months']:.1f} months)
- Risk band: {risk_profile.get('band')}
- Red flags: {risk_profile.get('red_flags', [])}

Your job: identify if this plan would:
(a) Drop the family's emergency fund below 3 months of essential expenses
(b) Increase debt-to-income to an unhealthy level
(c) Ignore upcoming fixed costs (rent cheque, school fees, insurance)

If you find a problem, output: "REVISE: <specific concern in one sentence>"
If the plan is sound, output: "APPROVED: <one sentence reason>"
""".strip()


def build_final_synthesis_prompt(query: str, all_findings: dict,
                                  disclaimer: str) -> str:
    """Prompt for Compliance Recommender to write the final user-facing answer."""
    return f"""
Synthesize a final answer to the user.

User's question: "{query}"

Team findings (use these, do not invent):
- Expense Analyzer's interpretation: {all_findings.get('expense_interpretation', 'N/A')}
- Risk Profiler's assessment: {all_findings.get('risk_band', 'N/A')} ({all_findings.get('risk_score', 'N/A')}/100)
- Goal Planner's recommended plan: {all_findings.get('goal_plan', 'N/A')}
- Critique outcome: {all_findings.get('critique_status', 'N/A')}

Write the final answer for the user. Structure:
1. Direct answer to their question (yes / no / "with conditions") — 1 sentence
2. The 2-3 most important findings (bullet points)
3. The specific recommended action plan
4. The required disclaimer (verbatim below)

Required disclaimer (include verbatim at the end):
{disclaimer}
""".strip()


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _format_categories(by_cat: dict, top_n: int = 8) -> str:
    items = list(by_cat.items())[:top_n]
    lines = [f"  - {cat}: AED {stats['avg_per_month']:,.0f}/month" for cat, stats in items]
    return "\n".join(lines) if lines else "  (no categories)"


def _format_options(options: list[dict]) -> str:
    if not options:
        return "  (no pre-computed options)"
    lines = []
    for o in options:
        lines.append(f"  • {o['label']}: {o.get('description', '')}")
    return "\n".join(lines)
