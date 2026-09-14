from backend.app.agent.prompts import (
    DECISION_SUMMARY_TEMPLATE,
    PENNY_SYSTEM_PROMPT,
    SPENDING_APPROVAL_TEMPLATE,
)


def test_system_prompt_content():
    """Ensures Penny system prompt incorporates vital financial invariants."""
    assert "Penny" in PENNY_SYSTEM_PROMPT
    assert "minimum balance" in PENNY_SYSTEM_PROMPT.lower()
    assert "90-day" in PENNY_SYSTEM_PROMPT.lower()
    assert "human-in-the-loop" in PENNY_SYSTEM_PROMPT.lower()


def test_spending_approval_template_formatting():
    """Ensures approval template formats without errors."""
    rendered = SPENDING_APPROVAL_TEMPLATE.format(
        currency="USD",
        amount=150.0,
        modifications="- Stop streaming ($15.00/mo)\n- Reduce dining to $50.00/mo",
    )
    assert "USD 150.00" in rendered
    assert "Stop streaming" in rendered
    assert "(Approve / Decline)" in rendered


def test_decision_summary_template_formatting():
    """Ensures decision summary template renders all safety indicators."""
    rendered = DECISION_SUMMARY_TEMPLATE.format(
        status="affordable",
        payment_method="full_payment",
        currency="USD",
        amount_safe=250.0,
        min_projected=1200.0,
        safety_floor=1000.0,
        explanation="Sufficient buffer throughout 90 days.",
    )
    assert "affordable" in rendered
    assert "USD 250.00" in rendered
    assert "USD 1,200.00" in rendered
