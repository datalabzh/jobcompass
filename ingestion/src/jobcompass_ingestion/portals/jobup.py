"""
jobup.py

Description : reads the result pages of a jobup.ch category.
Rules       : public result pages only (robots.txt: /api/ is forbidden).
              Category given by its URL slug, e.g. 'informatique-telecommunications'.
              The page embeds its data as JSON in a `__INIT__ = {...}` script:
                vacancy.results.main.meta     totalHits, numPages
                vacancy.results.main.results  the offers of the page
              Each offer is kept as raw JSON; its URL is built from its id.
              A page beyond the last one shows page 1 again: the number of pages
              comes from page 1, never from an empty page.
              Anything unexpected (HTTP status, missing block) raises
              ListingPageError, so the run stops without a snapshot record.
"""

import json

from jobcompass_ingestion.discover import ListingPage, ReadListingPage
from jobcompass_ingestion.fetch import FetchPage

SOURCE = "jobup"
LISTING_URL = "https://www.jobup.ch/fr/emplois/{category}/?page={page}"
OFFER_URL = "https://www.jobup.ch/fr/emplois/detail/{id}/"
_MARKER = "__INIT__"


class ListingPageError(Exception):
    """The result page could not be read as expected."""


def parse_listing_page(html: str) -> ListingPage:
    start = html.find(_MARKER)
    if start == -1:
        raise ListingPageError("no __INIT__ block")
    try:
        data, _ = json.JSONDecoder().raw_decode(html, html.index("{", start))
        main = data["vacancy"]["results"]["main"]
        offers = [
            (OFFER_URL.format(id=item["id"]), json.dumps(item, ensure_ascii=False))
            for item in main["results"]
        ]
        return ListingPage(
            announced_total=main["meta"].get("totalHits"),
            num_pages=int(main["meta"]["numPages"]),
            offers=offers,
        )
    except (ValueError, KeyError, TypeError) as error:
        raise ListingPageError(f"unexpected __INIT__ content: {error!r}") from error


def listing_reader(fetch_page: FetchPage, category: str) -> ReadListingPage:
    async def read_page(number: int) -> ListingPage:
        url = LISTING_URL.format(category=category, page=number)
        page = await fetch_page(url)
        if page.http_status != 200:
            raise ListingPageError(f"HTTP {page.http_status} on {url}")
        return parse_listing_page(page.content.decode("utf-8"))

    return read_page
