"""Provider registry — catalog of available data providers.

Thread-safe singleton that maps providers by name and category.
"""

from __future__ import annotations

from typing import Dict, List, Optional
from quant_nanggroe.engine.data.provider_interface import (
    DataCategory, QNAProviderBase,
)


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: Dict[str, QNAProviderBase] = {}

    def register(self, provider: QNAProviderBase) -> None:
        self._providers[provider.name] = provider

    def get(self, name: str) -> Optional[QNAProviderBase]:
        return self._providers.get(name)

    def list_providers(self) -> List[str]:
        return list(self._providers.keys())

    def get_by_category(self, category: DataCategory) -> List[QNAProviderBase]:
        return [p for p in self._providers.values()
                if hasattr(p, "categories") and category in p.categories]
