import logging
from typing import Any, List, Optional, Sequence
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool

from backend.app.config import settings

logger = logging.getLogger("penny.agent.supervisor")


class DeterministicFallbackChatModel(BaseChatModel):
    """
    Lightweight deterministic fallback chat model used when GROQ_API_KEY is not configured
    or during headless unit/integration testing.
    Supports tool binding and generates grounded responses.
    """
    default_response: Optional[AIMessage] = None

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        if self.default_response:
            msg = self.default_response
        else:
            msg = AIMessage(
                content="Hello! I am Penny, your financial assistant. I can help evaluate purchases and analyze cashflow safety."
            )
        return ChatResult(generations=[ChatGeneration(message=msg)])

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> Runnable:
        return self

    @property
    def _llm_type(self) -> str:
        return "deterministic_fallback_chat_model"


def resolve_agent_llm(
    llm: Optional[BaseChatModel] = None,
    tools: Optional[Sequence[BaseTool]] = None,
) -> Runnable:
    """
    Resolves the LLM for Penny agent execution.
    If GROQ_API_KEY is set, initializes ChatGroq.
    Otherwise, gracefully falls back to DeterministicFallbackChatModel.
    """
    if llm is not None:
        if tools and hasattr(llm, "bind_tools"):
            return llm.bind_tools(tools)
        return llm

    if settings.GROQ_API_KEY and settings.GROQ_API_KEY.strip():
        try:
            from langchain_groq import ChatGroq

            groq_llm = ChatGroq(
                model_name=settings.LLM_MODEL,
                groq_api_key=settings.GROQ_API_KEY,
                temperature=0.0,
            )
            if tools:
                return groq_llm.bind_tools(tools)
            return groq_llm
        except Exception as exc:
            logger.warning("Failed to initialize ChatGroq (%s); falling back to mock LLM.", exc)

    fallback = DeterministicFallbackChatModel()
    if tools:
        return fallback.bind_tools(tools)
    return fallback
