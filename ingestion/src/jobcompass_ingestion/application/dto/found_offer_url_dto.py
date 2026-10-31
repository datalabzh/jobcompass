"""
found_offer_url_dto.py

Description : an offer URL found by a discoverer on a result page.
Rules       : the discoverer only reports what it read; the use case adds the
              source, the method and the discovery time to build a DiscoveredOffer.
              params = context of the finding, e.g. {'category': '702', 'page': '3'}.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FoundOfferUrl:
    url: str
    params: dict[str, str] = field(default_factory=dict)
