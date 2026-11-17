"""
test_jobup_parser.py

Description : tests du parseur de jobup.ch.
Règles      : aucun réseau : le parseur reçoit un contenu. Deux vraies pages
              enregistrées (fixtures/) et des pages construites pour le test.
              Pages de résultats ('job_info') : nombre de pages, total, jobs et leur
              URL ; page sans __INIT__ refusée.
              Fiches ('job_detail') : champs lus sur une vraie page, description sans
              HTML, formes variables du JSON-LD, champs absents, page sans JobPosting
              ou au JSON illisible refusée.
              Type de page inconnu refusé.
"""

import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest

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


def detail(posting: dict[str, Any]) -> JobupJobDetail:
    """Parse a detail page whose JSON-LD holds a breadcrumb list and this posting."""
    breadcrumb: list[dict[str, Any]] = [{"@type": "BreadcrumbList"}]
    content: bytes = (
        f'<script type="application/ld+json">{json.dumps(breadcrumb)}</script>'
        f'<script type="application/ld+json">{json.dumps(posting)}</script>'
    ).encode()
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
    """A real job page gives its title, company, place, date and category."""
    job: object = PARSER.parse(
        JOB_DETAIL, (FIXTURES / "jobup_detail_page.html").read_bytes()
    )

    assert isinstance(job, JobupJobDetail)
    assert (job.title, job.company, job.postal_code) == (
        "Ingénieur·e software .NET 10",
        "Icube SA",
        "1700",
    )
    assert job.date_posted == date(2026, 11, 17)
    assert job.employment_types == ["Durée indéterminée"]
    assert job.categories[0].startswith("Informatique / Télécommunications")
    assert job.declared_skills == []
    assert "Ingénieur·e logiciel" in job.description and "<" not in job.description


def test_description_without_html() -> None:
    """The description is plain text, one line per HTML block."""
    job: JobupJobDetail = detail(
        {
            "@type": "JobPosting",
            "title": "T",
            "description": "<p>Python &amp; SQL</p><ul><li>dbt</li></ul>",
        }
    )
    assert job.description == "Python & SQL\ndbt"


def test_variable_shapes() -> None:
    """Lists or texts, objects or lists of objects, are all read as lists."""
    job: JobupJobDetail = detail(
        {
            "@type": "JobPosting",
            "title": "T",
            "employmentType": ["FULL_TIME", "PART_TIME"],
            "occupationalCategory": "Informatique",
            "skills": [{"@type": "DefinedTerm", "name": "Python"}, "SQL"],
            "jobLocation": [{"address": {"postalCode": 1201}}],
        }
    )
    assert job.employment_types == ["FULL_TIME", "PART_TIME"]
    assert job.categories == ["Informatique"]
    assert job.declared_skills == ["Python", "SQL"]
    assert job.postal_code == "1201"


def test_missing_fields() -> None:
    """Fields absent from the JSON-LD are None or empty lists."""
    job: JobupJobDetail = detail({"@type": "JobPosting", "title": "T"})
    assert (job.company, job.date_posted, job.postal_code) == (None, None, None)
    assert (job.description, job.employment_types, job.categories) == ("", [], [])


def test_detail_without_job_posting_refused() -> None:
    """A page without JSON-LD JobPosting, or with broken JSON, raises ParsingError."""
    for content in (
        b"<html><body>no JSON-LD here</body></html>",
        b'<script type="application/ld+json">{broken</script>',
    ):
        with pytest.raises(ParsingError, match="JobPosting"):
            PARSER.parse(JOB_DETAIL, content)


def test_unknown_kind_refused() -> None:
    """A page kind the parser does not know is a programming error."""
    with pytest.raises(ValueError, match="unknown page kind"):
        PARSER.parse("other", b"")
