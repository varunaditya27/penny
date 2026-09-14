from typing import Any, Optional
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.orm import Session

from backend.app.agent.checkpointers.memory import get_memory_checkpointer
from backend.app.agent.edges.routing import (
    route_from_agent,
    route_from_approval,
    route_from_tools,
)
from backend.app.agent.nodes.agent import create_agent_node
from backend.app.agent.nodes.approval import approval_node
from backend.app.agent.nodes.tools import create_tools_node
from backend.app.agent.state import AgentState
from backend.app.agent.supervisor import resolve_agent_llm
from backend.app.agent.tools.factory import create_agent_tools
from backend.core.pipeline import DecisionPipeline


def create_penny_agent(
    db: Session,
    llm: Optional[Any] = None,
    checkpointer: Optional[Any] = None,
    pipeline: Optional[DecisionPipeline] = None,
) -> CompiledStateGraph:
    """
    Constructs and compiles the modular Penny LangGraph financial assistant.
    Assembles partitioned nodes, edges, checkpointer, and tools without monolithic bloat.
    """
    # 1. Instantiate modular tools
    tools = create_agent_tools(db, pipeline=pipeline)

    # 2. Bind model with tools
    llm_with_tools = resolve_agent_llm(llm=llm, tools=tools)

    # 3. Create single-responsibility nodes
    agent_node = create_agent_node(llm_with_tools)
    tools_node = create_tools_node(tools)

    # 4. Construct state graph
    workflow = StateGraph(AgentState)

    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tools_node)
    workflow.add_node("approval", approval_node)

    # 5. Wire control flow edges
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges(
        "agent",
        route_from_agent,
        {"tools": "tools", "approval": "approval", END: END},
    )
    workflow.add_conditional_edges(
        "tools",
        route_from_tools,
        {"agent": "agent", "approval": "approval"},
    )
    workflow.add_conditional_edges(
        "approval",
        route_from_approval,
        {"agent": "agent", END: END},
    )

    # 6. Attach checkpointer for conversational persistence
    active_checkpointer = checkpointer if checkpointer is not None else get_memory_checkpointer()

    return workflow.compile(checkpointer=active_checkpointer)
