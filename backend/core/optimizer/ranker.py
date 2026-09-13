import logging
from typing import List, Optional

from backend.core.models.results import CandidatePlan

logger = logging.getLogger("buy_or_wait.optimizer.ranker")


class PlanRanker:
    """
    Ranks CandidatePlan objects according to the 6-tier tie-breaking rules:
    1. Complete by desired_completion_date (False before True for violations)
    2. Require no spending changes (False before True for violations)
    3. Minimize total amount paid (float)
    4. Start payment earlier (YYYY-MM-DD date string)
    5. Use fewer payments (integer count)
    6. Lowest payment_option_id (lexicographical string)
    """

    @classmethod
    def rank_candidates(cls, candidates: List[CandidatePlan]) -> List[CandidatePlan]:
        """Returns candidate plans sorted by 6-tier tie-breaking priority key."""
        return sorted(candidates, key=lambda p: p.ranking_key)

    @classmethod
    def select_best_plan(
        cls, candidates: List[CandidatePlan], fallback: Optional[CandidatePlan] = None
    ) -> Optional[CandidatePlan]:
        """
        Selects the highest-ranked candidate plan.
        Returns fallback if candidates list is empty.
        """
        if not candidates:
            return fallback

        ranked = cls.rank_candidates(candidates)
        return ranked[0]
