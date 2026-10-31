"""
test_discover_offers_use_case.py

Description : tests of the discover offers use case, with fakes.
Rules       : every observation is written, known URLs included; the discovery
              context is kept in discovery_params.
"""

from datetime import UTC, datetime

import pytest
from fakes.fake_connectors import FakeOfferDiscoverer
from fakes.in_memory_repositories import InMemoryDiscoveredOfferRepository

from jobcompass_contracts import DiscoveryMethod
from jobcompass_ingestion.application.dto.discover_offers_dto import (
    DiscoverOffersInput,
)
from jobcompass_ingestion.application.dto.found_offer_url_dto import FoundOfferUrl
from jobcompass_ingestion.application.use_cases.discover_offers_use_case import (
    DiscoverOffersUseCase,
)

NOW = datetime(2026, 10, 31, 6, 0, tzinfo=UTC)
REQUEST = DiscoverOffersInput(
    source="jobup",
    discovery_method=DiscoveryMethod.LISTING,
    discovery_params={"category": "702"},
)


def make_use_case(found, repository):
    return DiscoverOffersUseCase(
        discoverers={"jobup": FakeOfferDiscoverer(found)},
        discovered_offer_repository=repository,
        now=lambda: NOW,
    )


async def test_every_observation_written():
    repository = InMemoryDiscoveredOfferRepository()
    found = [
        FoundOfferUrl("https://www.jobup.ch/a", {"page": "1"}),
        FoundOfferUrl("https://www.jobup.ch/b", {"page": "1"}),
        FoundOfferUrl("https://www.jobup.ch/a", {"page": "2"}),
    ]

    output = await make_use_case(found, repository).execute(REQUEST)

    assert output.observed == 3
    assert output.distinct_urls == 2
    assert len(repository.offers) == 3


async def test_known_urls_written_again_on_next_run():
    repository = InMemoryDiscoveredOfferRepository()
    found = [FoundOfferUrl("https://www.jobup.ch/a")]
    use_case = make_use_case(found, repository)

    await use_case.execute(REQUEST)
    await use_case.execute(REQUEST)

    assert len(repository.offers) == 2


async def test_offer_built_with_run_context():
    repository = InMemoryDiscoveredOfferRepository()
    found = [FoundOfferUrl("https://www.jobup.ch/a", {"page": "3"})]

    await make_use_case(found, repository).execute(REQUEST)

    offer = repository.offers[0]
    assert offer.source == "jobup"
    assert offer.discovered_at == NOW
    assert offer.discovery_method == DiscoveryMethod.LISTING
    assert offer.discovery_params == {"category": "702", "page": "3"}


async def test_unknown_source_rejected():
    use_case = make_use_case([], InMemoryDiscoveredOfferRepository())
    request = DiscoverOffersInput("unknown", DiscoveryMethod.LISTING)
    with pytest.raises(ValueError):
        await use_case.execute(request)
