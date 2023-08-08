from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable
from uuid import UUID


@dataclass
class LLMContext:
    conversation_id: UUID
    prefix: list[str]

    @property
    def redis_key(self):
        return self.conversation_id.bytes


class LLM(ABC):
    @abstractmethod
    def infer(self, context: LLMContext) -> Iterable[str]:
        """Produce some text based on one context"""

    @abstractmethod
    def infer_batch(
        self, contexts: list[LLMContext]
    ) -> Iterable[tuple[LLMContext, str]]:
        """Produce mixed output from multiple contexts at once"""
