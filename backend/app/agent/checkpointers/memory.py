from langgraph.checkpoint.memory import MemorySaver


def get_memory_checkpointer() -> MemorySaver:
    """
    Returns an in-memory checkpointer for managing stateful conversational turns.
    Each session_id / thread_id maintains its independent conversation history and state.
    """
    return MemorySaver()
