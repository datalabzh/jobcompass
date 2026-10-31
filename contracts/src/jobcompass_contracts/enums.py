from enum import StrEnum


class DiscoveryMethod(StrEnum):
    """How an offer URL was discovered on a portal."""

    LISTING = "listing"  # paginated result pages (e.g. a category)
    SITEMAP = "sitemap"  # portal XML sitemap
    NEW_OFFERS = "new_offers"  # "latest offers" page
    KEYWORD = "keyword"  # keyword search
