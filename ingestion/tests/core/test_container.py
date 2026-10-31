"""
test_container.py

Description : tests of the dependency injection container.
Rules       : the use cases are assembled from the overridden dependencies and the
              settings; a missing infrastructure dependency is an error.
"""

import pytest
from dependency_injector import errors, providers
from fakes.fake_connectors import (
    FakeOfferDiscoverer,
    FakePageFetcher,
    InMemoryRawContentStorage,
)
from fakes.in_memory_repositories import (
    InMemoryDiscoveredOfferRepository,
    InMemoryFetchAttemptRepository,
    InMemoryRawOfferRepository,
)

from jobcompass_ingestion.application.use_cases.discover_offers_use_case import (
    DiscoverOffersUseCase,
)
from jobcompass_ingestion.application.use_cases.fetch_offers_use_case import (
    FetchOffersUseCase,
)
from jobcompass_ingestion.core.config import IngestionSettings
from jobcompass_ingestion.core.container import IngestionContainer


def make_container():
    container = IngestionContainer()
    container.settings.override(
        providers.Object(IngestionSettings(max_fetch_failures=5))
    )
    container.discoverers.override({"jobup": FakeOfferDiscoverer([])})
    container.page_fetcher.override(FakePageFetcher({}))
    container.raw_content_storage.override(InMemoryRawContentStorage())
    container.discovered_offer_repository.override(InMemoryDiscoveredOfferRepository())
    container.raw_offer_repository.override(InMemoryRawOfferRepository())
    container.fetch_attempt_repository.override(InMemoryFetchAttemptRepository())
    return container


def test_use_cases_assembled():
    container = make_container()
    assert isinstance(container.discover_offers_use_case(), DiscoverOffersUseCase)
    fetch = container.fetch_offers_use_case()
    assert isinstance(fetch, FetchOffersUseCase)
    assert fetch._max_failures == 5


def test_missing_dependency_is_an_error():
    with pytest.raises(errors.Error):
        IngestionContainer().fetch_offers_use_case()


def test_default_settings():
    settings = IngestionSettings(_env_file=None)
    assert settings.max_fetch_failures == 3
