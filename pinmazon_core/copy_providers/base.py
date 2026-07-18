from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from pinmazon_core.schemas import CopyPackage


@dataclass(frozen=True)
class PinCopyRequest:
    product: dict
    angle: str
    audience: str
    board: str
    funnel: str
    variant_index: int = 0


class CopyProvider(Protocol):
    def generate(self, request: PinCopyRequest) -> CopyPackage: ...
