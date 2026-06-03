"""
CrewAI agent definitions for the Personal Finance system.

5 specialist agents with clear roles and backstories. Each agent has a
non-trivial role in the collaboration:

  Expense Analyzer       - PARSES and INTERPRETS spending data
  Risk Profiler          - CHALLENGES aggressive plans, flags red flags
  Investment Advisor     - PROPOSES allocations, must defend against critic
  Goal Planner           - SETS milestones, pushes back on unrealistic timelines
  Compliance Recommender - SYNTHESIZES + has VETO power if disclaimers missing

These are CrewAI Agent objects; the orchestrator in crew.py drives the
actual collaboration (which is non-linear, with feedback loops).
"""

from typing import Optional


def build_agents(agent_llm, reasoning_llm):
    """
    Construct the 5 CrewAI agents.

    Returns a dict keyed by short agent code. If LLMs are None (sample mode),
    returns lightweight stand-ins with the same .role attribute so the
    orchestrator code path is identical.
    """
    if agent_llm is None or reasoning_llm is None:
        return _build_sample_agents()

    # Lazy import so we don't require crewai in sample mode
    from crewai import Agent

    expense_analyzer = Agent(
        role="Expense Analyzer",
        goal=(
            "Parse the user's bank statements, categorize every transaction, "
            "and produce a clear month-by-month picture of where money goes. "
            "Surface anomalies, duplicate subscriptions, and high-leverage cut targets."
        ),
        backstory=(
            "You are a meticulous financial analyst with 10 years of experience "
            "reviewing UAE consumer banking data. You know the difference between "
            "essential spend (rent, school fees, utilities) and discretionary spend "
            "(food delivery, subscriptions, dining out). You speak in numbers."
        ),
        llm=agent_llm,
        allow_delegation=False,
        verbose=False,
    )

    risk_profiler = Agent(
        role="Risk Profiler",
        goal=(
            "Assess the user's financial risk tolerance based on their income "
            "stability, dependents, emergency fund, and debt obligations. "
            "Aggressively challenge ANY plan that would compromise the family's "
            "emergency cushion or push them into unsustainable territory."
        ),
        backstory=(
            "You are a conservative, family-oriented UAE financial planner. "
            "You have seen too many expats lose visa status due to financial shocks "
            "and you ALWAYS prioritize liquidity and emergency runway. You are "
            "willing to push back on the Investment Advisor and Goal Planner when "
            "they propose plans that don't account for family risk."
        ),
        llm=reasoning_llm,
        allow_delegation=False,
        verbose=False,
    )

    investment_advisor = Agent(
        role="Investment Advisor",
        goal=(
            "Recommend concrete investment or savings products matching the user's "
            "risk profile and goals. Default to UAE-available products (Sukuk, "
            "Sarwa, ADCB Active Saver, Stake). Support Sharia-compliant toggle. "
            "Revise your recommendations if the Risk Profiler rejects them."
        ),
        backstory=(
            "You are a UAE-based wealth advisor familiar with both conventional and "
            "Sharia-compliant products. You match products to user goals — not just "
            "what's hot. You accept criticism from the Risk Profiler gracefully "
            "and revise plans to be safer when challenged."
        ),
        llm=agent_llm,
        allow_delegation=False,
        verbose=False,
    )

    goal_planner = Agent(
        role="Goal Planner",
        goal=(
            "Translate the user's actual question (buy a car / take a vacation / "
            "cut expenses) into a concrete, dated plan with milestones. Refuse to "
            "endorse unrealistic timelines — push back if the math doesn't work."
        ),
        backstory=(
            "You are a no-nonsense financial coach. You translate vague wishes "
            "into milestones with specific AED amounts and dates. If the user "
            "wants something they can't afford in their timeline, you say so "
            "directly and propose 3 alternative paths."
        ),
        llm=reasoning_llm,
        allow_delegation=False,
        verbose=False,
    )

    compliance_recommender = Agent(
        role="Compliance Recommender",
        goal=(
            "Synthesize the team's findings into the FINAL answer for the user. "
            "Ensure required disclaimers are present. If any critical info or "
            "disclaimer is missing, refuse to finalize and send back for revision."
        ),
        backstory=(
            "You are the safety net for the team. You speak in clear, plain English "
            "(or Arabic if requested). You never give investment advice without a "
            "disclaimer that this is AI-generated guidance, not personalized advice "
            "from a licensed advisor. You have VETO power."
        ),
        llm=reasoning_llm,
        allow_delegation=False,
        verbose=False,
    )

    return {
        "expense_analyzer": expense_analyzer,
        "risk_profiler": risk_profiler,
        "investment_advisor": investment_advisor,
        "goal_planner": goal_planner,
        "compliance_recommender": compliance_recommender,
    }


# ---------------------------------------------------------------------------
# Sample-mode stand-ins (no LLM needed)
# ---------------------------------------------------------------------------

class _SampleAgent:
    """Minimal duck-typed Agent for SAMPLE_MODE — no LLM calls."""
    def __init__(self, role: str, goal: str):
        self.role = role
        self.goal = goal


def _build_sample_agents():
    return {
        "expense_analyzer":      _SampleAgent("Expense Analyzer",
            "Parse statements and categorize spend"),
        "risk_profiler":         _SampleAgent("Risk Profiler",
            "Assess risk tolerance and challenge aggressive plans"),
        "investment_advisor":    _SampleAgent("Investment Advisor",
            "Recommend products matching risk profile"),
        "goal_planner":          _SampleAgent("Goal Planner",
            "Translate questions into dated milestones"),
        "compliance_recommender":_SampleAgent("Compliance Recommender",
            "Final synthesis with disclaimers"),
    }
