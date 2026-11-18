"""
test_jobup_parser.py

Description : tests du parseur de jobup.ch.
Règles      : aucun réseau : le parseur reçoit un contenu. Deux vraies pages
              enregistrées (fixtures/) et des pages construites pour le test.
              Pages de résultats ('job_info') : nombre de pages, total, jobs et leur
              URL ; page sans __INIT__ refusée.
              Fiches ('job_detail') : bloc JSON-LD du JobPosting gardé tel quel (vraie
              page, plusieurs blocs) ; à défaut (pas de JSON-LD, JSON illisible),
              paragraphes du texte visible, sans script ni style.
              Type de page inconnu refusé.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from contracts import PayloadFormat
from extraction.jobup.jobup_parser import (
    JOB_DETAIL,
    JOB_INFO,
    JobupJobDetail,
    JobupListing,
    JobupParser,
)
from interfaces import ParsingError

FIXTURES: Path = Path(__file__).parent / "fixtures"
PARSER: JobupParser = JobupParser()


def detail(content: bytes) -> JobupJobDetail:
    """Parse a detail page."""
    result: object = PARSER.parse(JOB_DETAIL, content)
    assert isinstance(result, JobupJobDetail)
    return result


# --- result pages ---------------------------------------------------------------


def test_real_listing_page() -> None:
    """A real result page gives its page count, its total and its jobs."""
    listing: object = PARSER.parse(
        JOB_INFO, (FIXTURES / "jobup_listing_page.html").read_bytes()
    )

    assert isinstance(listing, JobupListing)
    assert (listing.num_pages, listing.total, len(listing.jobs)) == (40, 786, 22)
    assert listing.jobs[0].card["title"] == "Financial Analyst & AI Engineer"
    assert listing.jobs[0].url == (
        "https://www.jobup.ch/fr/emplois/detail/18943dd6-c820-41e9-9e37-0da70fd57866/"
    )


def test_listing_without_data_refused() -> None:
    """A result page without the __INIT__ block raises ParsingError."""
    with pytest.raises(ParsingError, match="__INIT__"):
        PARSER.parse(JOB_INFO, b"<html>Denied</html>")


# --- job details ----------------------------------------------------------------


def test_real_detail_page() -> None:
    """A real job page gives its JSON-LD JobPosting block, as in the page."""
    job: JobupJobDetail = detail((FIXTURES / "jobup_detail_page.html").read_bytes())

    assert job.payload_format == PayloadFormat.JSON_LD
    posting: dict[str, Any] = json.loads(job.payload)
    assert posting["@type"] == "JobPosting"
    assert posting["title"] == "Ingénieur·e software .NET 10"
    assert posting["hiringOrganization"]["name"] == "Icube SA"


def test_job_posting_block_kept_as_is() -> None:
    """Among several JSON-LD blocks, the JobPosting one is kept, text unchanged."""
    breadcrumb: str = json.dumps([{"@type": "BreadcrumbList"}])
    posting: str = '{"@type": "JobPosting",  "title": "T", "x": "<p>a</p>"}'
    job: JobupJobDetail = detail(
        (
            f'<script type="application/ld+json">{breadcrumb}</script>'
            f'<script type="application/ld+json">\n{posting}\n</script>'
        ).encode()
    )
    assert (job.payload_format, job.payload) == (PayloadFormat.JSON_LD, posting)


def test_paragraphs_without_job_posting() -> None:
    """Without JSON-LD JobPosting, the visible text of the page, by paragraph."""
    for content in (
        b"<html><head><style>p {}</style><script>var x;</script></head>"
        b"<body><h1>Data  Engineer</h1><p>Python &amp; SQL</p><li>dbt</li></body>",
        b'<script type="application/ld+json">{broken</script>'
        b"<h1>Data Engineer</h1><p>Python &amp; SQL</p><li>dbt</li>",
    ):
        job: JobupJobDetail = detail(content)
        assert job.payload_format == PayloadFormat.PARAGRAPHS
        assert json.loads(job.payload) == ["Data Engineer", "Python & SQL", "dbt"]


def test_unknown_kind_refused() -> None:
    """A page kind the parser does not know is a programming error."""
    with pytest.raises(ValueError, match="unknown page kind"):
        PARSER.parse("other", b"")
