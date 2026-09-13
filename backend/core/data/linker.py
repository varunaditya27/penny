import logging
from typing import List, Dict, Set
from backend.core.models.domain import FinancialEvent

logger = logging.getLogger("buy_or_wait.linker")


class EventLinker:
    """
    Handles 5-way type-dispatch resolution for events with linked_event_id.
    Prevents duplicate double-counting and filters out non-cash transactions.
    """

    @classmethod
    def resolve_linked_events(cls, events: List[FinancialEvent]) -> List[FinancialEvent]:
        """
        Processes a list of financial events, resolving linked records by type:
        1. refund: Keep both original debit and settled reversal credit (ignore pending refund credits).
        2. expense: Collapse authorization + settled pairs into the single settled charge.
        3. investment_valuation: Exclude entirely (non-cash mark-to-market).
        4. debt_payment: Keep as distinct real cash payments.
        5. investment_sale: Keep cash proceeds credit, exclude non-cash purchase basis.
        """
        events_by_id: Dict[str, FinancialEvent] = {e.event_id: e for e in events}
        excluded_ids: Set[str] = set()

        for event in events:
            # Check unrealized investment valuations (linked or unlinked)
            if event.event_type == "investment_valuation" or event.status == "unrealized":
                excluded_ids.add(event.event_id)
                continue

            if not event.linked_event_id:
                continue

            parent = events_by_id.get(event.linked_event_id)
            if not parent:
                continue

            linked_type = event.event_type

            if linked_type == "expense":
                # Expense linked to expense (e.g. card auth -> settled purchase or duplicate)
                if parent.status == "cancelled" and event.status == "settled":
                    excluded_ids.add(parent.event_id)
                elif parent.status == "settled" and event.status == "cancelled":
                    excluded_ids.add(event.event_id)
                elif "duplicate" in event.description.lower() and event.status == "pending":
                    # Possible duplicate charge flagged by bank - do not double debit
                    excluded_ids.add(event.event_id)
                elif parent.event_type == "expense" and event.status == "settled" and parent.status == "settled":
                    # If amounts match and timestamps close, keep child
                    if parent.amount == event.amount:
                        excluded_ids.add(parent.event_id)

            elif linked_type == "refund":
                # Real cash movement reversal
                # If refund is pending, it must NOT be counted as cash yet (problem statement rule)
                if event.status == "pending":
                    excluded_ids.add(event.event_id)
                # If settled, keep both original debit and refund credit

            elif linked_type == "investment_valuation":
                excluded_ids.add(event.event_id)
                excluded_ids.add(parent.event_id)

            elif linked_type == "investment_sale":
                # Keep the cash proceeds from sale, exclude purchase non-cash basis
                if parent.event_type == "investment_purchase":
                    excluded_ids.add(parent.event_id)

            elif linked_type == "debt_payment":
                # Distinct payments, keep both unless one is cancelled
                if parent.status == "cancelled":
                    excluded_ids.add(parent.event_id)
                if event.status == "cancelled":
                    excluded_ids.add(event.event_id)

        # Filter and return
        filtered_events = [e for e in events if e.event_id not in excluded_ids]
        logger.debug(
            f"EventLinker resolved {len(events)} events down to {len(filtered_events)} (excluded {len(excluded_ids)} linked/non-cash records)"
        )
        return filtered_events
