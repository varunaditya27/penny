import json
import pytest
from backend.app.agent.tools import create_agent_tools


def test_create_agent_tools_bundle(db_session):
    """Verifies that all required financial tools are created and named properly."""
    tools = create_agent_tools(db_session)
    tool_names = {t.name for t in tools}

    expected_tools = {
        "evaluate_purchase",
        "get_cashflow_trajectory",
        "get_user_financial_profile",
        "simulate_spending_reduction",
        "request_spending_modification_approval",
    }
    assert expected_tools.issubset(tool_names)


def test_evaluate_purchase_tool(db_session):
    """Tests evaluation tool invocation against seeded test database."""
    tools = create_agent_tools(db_session)
    eval_tool = next(t for t in tools if t.name == "evaluate_purchase")

    raw_output = eval_tool.invoke({
        "user_id": "user_01",
        "requested_amount": 50.0,
        "desired_completion_date": "2026-06-01",
        "allows_partial": False,
    })
    data = json.loads(raw_output)

    assert "affordability_status" in data
    assert "amount_safe_to_pay" in data
    assert "payment_method" in data
    assert "explanation" in data
    assert "payment_plan" in data
    assert "earliest_date_for_full_payment" in data


def test_get_cashflow_trajectory_tool(db_session):
    """Tests cashflow trajectory simulation tool output and sampling."""
    tools = create_agent_tools(db_session)
    traj_tool = next(t for t in tools if t.name == "get_cashflow_trajectory")

    raw_output = traj_tool.invoke({
        "user_id": "user_01",
        "prospective_amount": 100.0,
        "days": 90,
    })
    data = json.loads(raw_output)

    assert data["user_id"] == "user_01"
    assert "sampled_trajectory" in data
    assert len(data["sampled_trajectory"]) > 0
    assert "lowest_projected_balance" in data


def test_get_user_financial_profile_tool(db_session):
    """Tests profile and cashflow risk retrieval tool."""
    tools = create_agent_tools(db_session)
    profile_tool = next(t for t in tools if t.name == "get_user_financial_profile")

    raw_output = profile_tool.invoke({"user_id": "user_01"})
    data = json.loads(raw_output)

    assert data["user_id"] == "user_01"
    assert "home_currency" in data
    assert "minimum_balance_to_keep" in data
    assert "current_available_balance" in data


def test_simulate_spending_reduction_tool(db_session):
    """Tests spending reduction simulation on flexible categories."""
    tools = create_agent_tools(db_session)
    spending_tool = next(t for t in tools if t.name == "simulate_spending_reduction")

    raw_output = spending_tool.invoke({
        "user_id": "user_01",
        "category": "Dining Out",
        "reduction_pct": 0.5,
    })
    data = json.loads(raw_output)
    assert "allowed" in data


def test_request_spending_modification_approval_tool(db_session):
    """Tests human-in-the-loop approval initiation tool."""
    tools = create_agent_tools(db_session)
    approval_tool = next(t for t in tools if t.name == "request_spending_modification_approval")

    raw_output = approval_tool.invoke({
        "user_id": "user_01",
        "category": "Subscriptions",
        "reduction_amount": 25.0,
        "reason": "Afford new tablet purchase",
    })
    data = json.loads(raw_output)

    assert data["status"] == "pending_user_confirmation"
    assert "action_id" in data
    assert data["reduction_amount"] == 25.0
