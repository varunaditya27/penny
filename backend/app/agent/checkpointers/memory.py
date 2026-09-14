from typing import Optional
from langgraph.checkpoint.memory import MemorySaver

_default_checkpointer: Optional[MemorySaver] = None


def get_memory_checkpointer(fresh: bool = False) -> MemorySaver:
    """
    Returns an in-memory checkpointer for managing stateful conversational turns.
    Each session_id / thread_id maintains its independent conversation history and state.
    By default returns a shared checkpointer instance across requests so conversational
    and approval state is preserved for the same session_id.
    Passing fresh=True creates a new checkpointer (useful for isolated tests).
    """
    global _default_checkpointer
    if fresh or _default_checkpointer is None:
        cp = MemorySaver()
        if not fresh:
            _default_checkpointer = cp
        return cp
    return _default_checkpointer


def reset_memory_checkpointer() -> None:
    """Resets the singleton checkpointer, clearing all in-memory threads."""
    global _default_checkpointer
    _default_checkpointer = None
