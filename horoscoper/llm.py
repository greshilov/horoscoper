from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterable
from uuid import UUID, uuid4


@dataclass
class LLMContext:
    id: UUID = field(default_factory=uuid4)
    prefix: str = ""

    @property
    def redis_key(self) -> bytes:
        return self.id.bytes

    def __repr__(self) -> str:
        return f"LLMContext({self.id}, prefix: {self.prefix})"


@dataclass
class LLMInferResult:
    text: str
    is_last_chunk: bool = False


# This type represents `inference slice` produced from multiple contexts
LLMInferBatchResult = list[tuple[LLMContext, LLMInferResult]]


class LLM(ABC):
    @abstractmethod
    def infer(self, context: LLMContext) -> Iterable[LLMInferResult]:
        """Produce some text based on one context"""

    @abstractmethod
    def infer_batch(self, contexts: list[LLMContext]) -> Iterable[LLMInferBatchResult]:
        """Produce mixed output from multiple contexts at once"""
