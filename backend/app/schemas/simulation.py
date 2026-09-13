from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class TrajectoryPoint(BaseModel):
    date: str
    baseline_balance: float
    with_purchase_balance: Optional[float] = None


class TrajectoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    currency: str
    minimum_balance_to_keep: float
    points: List[TrajectoryPoint]
    lowest_projected_balance: float
    is_safe: bool
