from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable
from uuid import UUID


@dataclass
class LLMContext:
    conversation_id: UUID
    prefix: list[str]


class LLM(ABC):
    @abstractmethod
    def infer(self, context: LLMContext) -> Iterable[str]:
        """Produce some text based on one context"""

    @abstractmethod
    def infer_batch(
        self, contexts: list[LLMContext]
    ) -> Iterable[tuple[LLMContext, str]]:
        """Produce mixed output from multiple contexts at once"""
