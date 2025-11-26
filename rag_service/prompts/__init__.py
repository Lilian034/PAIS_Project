"""
Prompt 模板模組
包含所有 LangChain Agent 和 Chain 的 Prompt 模板
"""

from .public_agent import PUBLIC_AGENT_PROMPT
from .staff_agent import STAFF_AGENT_PROMPT

__all__ = [
    'PUBLIC_AGENT_PROMPT',
    'STAFF_AGENT_PROMPT',
]
