"""Pydantic models for API I/O and shared agent state."""

from typing import Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# API request / response
# ---------------------------------------------------------------------------

class RunContext(BaseModel):
    user_id: str | None = None
    csv_files: list[str] | None = None
    profile_file: str | None = None


class RunRequest(BaseModel):
    query: str = Field(..., description="The user's finance question")
    context: RunContext | None = None


class AgentTrace(BaseModel):
    """One entry in the agent collaboration trace."""
    timestamp: str
    agent_name: str
    action: str
    target_agent: str | None = None
    input_summary: str | None = None
    output_summary: str | None = None
    status: str = "completed"
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunResponse(BaseModel):
    use_case_id: str = "24"
    query: str
    answer: str
    agents_involved: list[str]
    trace_path: str
    elapsed_seconds: float
    sample_mode: bool
    findings: dict[str, Any] = Field(default_factory=dict)
    trace_events: list[dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------

class Transaction(BaseModel):
    date: str               # ISO format
    description: str
    amount: float           # positive number
    kind: str               # "debit" or "credit"
    account: str            # "savings" or "credit_card"
    category: str | None = None


class FinancialSummary(BaseModel):
    monthly_income_aed: float
    monthly_fixed_costs_aed: float
    monthly_variable_costs_aed: float
    monthly_savings_aed: float
    savings_rate_pct: float
    current_buffer_aed: float
    buffer_months: float
    by_category: dict[str, float] = Field(default_factory=dict)  # avg/month
    insights: list[str] = Field(default_factory=list)


class RiskProfile(BaseModel):
    score: int               # 0-100
    band: str                # "conservative" | "moderate" | "aggressive"
    rationale: list[str]
    red_flags: list[str] = Field(default_factory=list)


class GoalPlan(BaseModel):
    feasible: bool
    months_required: float | None = None
    monthly_savings_needed: float | None = None
    options: list[dict[str, Any]] = Field(default_factory=list)
    recommended_option: str | None = None
