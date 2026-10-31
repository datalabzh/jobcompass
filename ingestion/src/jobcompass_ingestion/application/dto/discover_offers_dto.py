"""
discover_offers_dto.py

Description : input and output of the discover offers use case.
Rules       : input = what to explore (source, method, parameters such as the
              category), built by the entry point.
              output = counts only, for the logs and the orchestrator.
"""

from dataclasses import dataclass, field

from jobcompass_contracts import DiscoveryMethod


@dataclass(frozen=True)
class DiscoverOffersInput:
    source: str
    discovery_method: DiscoveryMethod
    discovery_params: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class DiscoverOffersOutput:
    observed: int  # URLs written, one per observation
    distinct_urls: int
