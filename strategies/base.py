from abc import ABC, abstractmethod
from typing import Optional


class BaseMatchStrategy(ABC):
    @abstractmethod
    def match(
        self,
        logic,
        sources: list,
        dests: list,
        recommendations: list,
        mode: str,
        article: str,
        transfer_sites: set,
        receive_sites: set,
        source_to_receive_sites: dict,
        received_qty_by_site: dict,
        matched_sites: set,
        receive_site_limit: Optional[int],
        **kwargs,
    ) -> list:
        pass
