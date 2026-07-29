from typing import Optional, TypedDict


class ActiveMediaModel(TypedDict, total=False):
    provider: str
    model: Optional[str]
