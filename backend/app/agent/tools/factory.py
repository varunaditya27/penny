from typing import List, Optional
from langchain_core.tools import BaseTool
from sqlalchemy.orm import Session

from backend.app.agent.tools.evaluation import create_evaluation_tool
from backend.app.agent.tools.profile import create_profile_tool
from backend.app.agent.tools.spending import create_spending_tools
from backend.app.agent.tools.trajectory import create_trajectory_tool
from backend.core.pipeline import DecisionPipeline


def create_agent_tools(
    db: Session,
    pipeline: Optional[DecisionPipeline] = None,
) -> List[BaseTool]:
    """
    Factory aggregating all modular agent tools into a unified tool list.
    Each tool module is cleanly decoupled with a single domain responsibility.
    """
    tools: List[BaseTool] = [
        create_evaluation_tool(db, pipeline=pipeline),
        create_trajectory_tool(db),
        create_profile_tool(db),
    ]
    tools.extend(create_spending_tools(db))
    return tools
