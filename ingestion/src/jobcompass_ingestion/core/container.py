"""
container.py

Description : dependency injection container of the ingestion brick.
Rules       : the only place where implementations are chosen and assembled.
              Infrastructure dependencies are declared as abstract: the entry point
              provides the real connectors, tests provide fakes (override).
              Use cases receive settings values, never the settings object.
"""

from dependency_injector import containers, providers

from jobcompass_ingestion.application.interfaces.i_discovered_offer_repository import (
    IDiscoveredOfferRepository,
)
from jobcompass_ingestion.application.interfaces.i_fetch_attempt_repository import (
    IFetchAttemptRepository,
)
from jobcompass_ingestion.application.interfaces.i_page_fetcher import IPageFetcher
from jobcompass_ingestion.application.interfaces.i_raw_content_storage import (
    IRawContentStorage,
)
from jobcompass_ingestion.application.interfaces.i_raw_offer_repository import (
    IRawOfferRepository,
)
from jobcompass_ingestion.application.use_cases.discover_offers_use_case import (
    DiscoverOffersUseCase,
)
from jobcompass_ingestion.application.use_cases.fetch_offers_use_case import (
    FetchOffersUseCase,
)
from jobcompass_ingestion.core.config import IngestionSettings


class IngestionContainer(containers.DeclarativeContainer):
    settings = providers.Singleton(IngestionSettings)

    # Infrastructure: provided by the entry point (step 2) or by the tests.
    discoverers = providers.Dependency(instance_of=dict)
    page_fetcher = providers.Dependency(instance_of=IPageFetcher)
    raw_content_storage = providers.Dependency(instance_of=IRawContentStorage)
    discovered_offer_repository = providers.Dependency(
        instance_of=IDiscoveredOfferRepository
    )
    raw_offer_repository = providers.Dependency(instance_of=IRawOfferRepository)
    fetch_attempt_repository = providers.Dependency(instance_of=IFetchAttemptRepository)

    discover_offers_use_case = providers.Factory(
        DiscoverOffersUseCase,
        discoverers=discoverers,
        discovered_offer_repository=discovered_offer_repository,
    )

    fetch_offers_use_case = providers.Factory(
        FetchOffersUseCase,
        page_fetcher=page_fetcher,
        raw_content_storage=raw_content_storage,
        discovered_offer_repository=discovered_offer_repository,
        raw_offer_repository=raw_offer_repository,
        fetch_attempt_repository=fetch_attempt_repository,
        scraper_version=settings.provided.scraper_version,
        max_failures=settings.provided.max_fetch_failures,
        max_concurrency=settings.provided.fetch_max_concurrency,
        batch_size=settings.provided.fetch_batch_size,
    )
