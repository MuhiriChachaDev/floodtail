"""LangChain-oriented long-term agent memory backed by Postgres (pgvector).

Stores:
- Semantic memories (facts / summaries) with embeddings for recall
- Session chat message history for multi-turn context

Falls back to in-memory when Postgres is unavailable.
"""

from packages.memory.longterm import (
    AgentMemory,
    MemoryRecord,
    get_agent_memory,
    recall_memories,
    remember,
)

__all__ = [
    "AgentMemory",
    "MemoryRecord",
    "get_agent_memory",
    "recall_memories",
    "remember",
]
