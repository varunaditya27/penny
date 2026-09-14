import json
from typing import Optional
from langchain_core.tools import BaseTool, tool
from sqlalchemy.orm import Session

from backend.app.services.simulation_service import SimulationService


def create_trajectory_tool(db: Session) -> BaseTool:
    simulation_service = SimulationService(db)

    @tool
    def get_cashflow_trajectory(
        user_id: str,
        prospective_amount: Optional[float] = None,
        start_date: Optional[str] = None,
        days: int = 90,
    ) -> str:
        """
        Computes the forward daily cashflow trajectory over 90 days.
        Compares baseline trajectory with prospective purchase impact.
        Returns safety minimums, potential balance breaches, and summary trajectory points.
        """
        try:
            res = simulation_service.compute_user_trajectory(
                user_id=user_id,
                prospective_amount=prospective_amount,
                start_date=start_date,
                days=days,
            )
            # Sample trajectory to avoid overflowing context window (every 7 days plus first/last)
            sampled_points = []
            for idx, pt in enumerate(res.points):
                if idx == 0 or idx == len(res.points) - 1 or idx % 7 == 0:
                    sampled_points.append(pt.model_dump())

            return json.dumps(
                {
                    "user_id": res.user_id,
                    "currency": res.currency,
                    "minimum_balance_to_keep": res.minimum_balance_to_keep,
                    "lowest_projected_balance": res.lowest_projected_balance,
                    "is_safe": res.is_safe,
                    "sampled_trajectory": sampled_points,
                    "total_points_simulated": len(res.points),
                }
            )

        except Exception as exc:
            return json.dumps({"error": str(exc)})

    return get_cashflow_trajectory
