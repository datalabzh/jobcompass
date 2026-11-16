"""
test_jobup_job_details.py

Description : tests des job details de jobup.ch.
Règles      : un résultat par URL ; une page 2xx donne son reçu (hash du contenu)
              et son contenu inchangé ; un statut non 2xx ou l'absence de réponse
              donne un journal d'échec avec la raison, sans arrêter le lot.
"""

from conftest import FakeGetPage, fixed_now, page

from contracts import JobDetailExtractionLog, compute_raw_hash
from extraction.interfaces.i_job_details_extractor import (
    FetchedJobDetail,
    JobDetailResult,
)
from extraction.jobup.jobup_job_details import JobupJobDetails

OK: str = "https://www.jobup.ch/fr/emplois/detail/ok/"
GONE: str = "https://www.jobup.ch/fr/emplois/detail/gone/"
DOWN: str = "https://www.jobup.ch/fr/emplois/detail/down/"


def test_one_result_per_url() -> None:
    """Success, 404 and no answer each give their result, in order."""
    get_page: FakeGetPage = FakeGetPage({OK: page(), GONE: page(status=404)})
    details: JobupJobDetails = JobupJobDetails(get_page, "jobup", False, fixed_now)

    results: list[JobDetailResult] = details.execute([OK, GONE, DOWN])

    fetched, gone, down = results
    assert isinstance(fetched, FetchedJobDetail)
    assert fetched.content == b"<html>job</html>"
    assert fetched.job_detail.raw_hash == compute_raw_hash(b"<html>job</html>")
    assert fetched.job_detail.scraper_version == JobupJobDetails.version
    assert isinstance(gone, JobDetailExtractionLog) and gone.error == "HTTP 404"
    assert isinstance(down, JobDetailExtractionLog)
    assert down.error.startswith("no answer")
