SPENDING_APPROVAL_TEMPLATE = """To afford this purchase of {currency} {amount:,.2f}, our simulation found a viable plan that requires modifying recurring expenses:
{modifications}

Would you like to proceed with this budget modification? (Approve / Decline)"""

DECISION_SUMMARY_TEMPLATE = """Affordability Assessment:
- Status: {status}
- Recommended Method: {payment_method}
- Amount Safe to Pay: {currency} {amount_safe:,.2f}
- Lowest Projected Balance: {currency} {min_projected:,.2f} (Safety Floor: {currency} {safety_floor:,.2f})
- Rationale: {explanation}"""
