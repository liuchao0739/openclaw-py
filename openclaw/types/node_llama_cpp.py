from enum import IntEnum
from typing import Any, Awaitable, Callable, List, Optional, Union


class LlamaLogLevel(IntEnum):
    error = 0


class LlamaEmbedding:
    vector: Union[List[float], Any]


class LlamaEmbeddingContext:
    async def getEmbeddingFor(self, text: str) -> LlamaEmbedding:
        ...

    def dispose(self) -> Optional[Awaitable[None]]:
        ...


class LlamaModel:
    async def createEmbeddingContext(self, options: Optional[dict] = None) -> LlamaEmbeddingContext:
        ...

    def dispose(self) -> Optional[Awaitable[None]]:
        ...


class ResolveModelFileOptions:
    directory: Optional[str]
    signal: Optional[Any]


class Llama:
    async def loadModel(self, model_path: str, load_signal: Optional[Any] = None) -> LlamaModel:
        ...

    def dispose(self) -> Optional[Awaitable[None]]:
        ...


def getLlama(params: dict) -> Awaitable[Llama]:
    ...


def resolveModelFile(
    model_path: str,
    options_or_directory: Optional[Union[str, ResolveModelFileOptions]] = None,
) -> Awaitable[str]:
    ...
