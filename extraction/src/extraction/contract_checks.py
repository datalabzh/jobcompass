"""
contract_checks.py

Description : vérifie ce que renvoient les classes d'un site, avant toute écriture.
Règles      : la classe abstraite oblige à écrire execute, mais rien n'empêche à
              l'exécution de renvoyer autre chose que le contrat : chaque page de
              job infos et chaque lot de job details est donc contrôlé ici.
              Contrôles : bon type, bonne source, bon is_test ; pour les job details,
              un résultat par URL demandée, et raw_hash conforme au HTML reçu.
              Une violation lève ContractViolationError : c'est un bug du code du
              site, le passage s'arrête et rien d'invalide n'est écrit.
"""

from contracts import JobDetailExtractionLog, JobInfo, compute_raw_hash
from extraction.interfaces.i_job_details_extractor import FetchedJobDetail
from extraction.interfaces.i_job_infos_extractor import JobInfoPage


class ContractViolationError(Exception):
    """A site class returned something that does not respect its contract."""


def check_job_info_page(page: object, source: str, is_test: bool) -> JobInfoPage:
    """The page, if it is a JobInfoPage of JobInfo of this run; error otherwise."""
    if not isinstance(page, JobInfoPage):
        raise ContractViolationError(f"expected JobInfoPage, got {type(page)}")
    for job_info in page.job_infos:
        if not isinstance(job_info, JobInfo):
            raise ContractViolationError(f"expected JobInfo, got {type(job_info)}")
        _check_origin(job_info.source, job_info.is_test, source, is_test)
    return page


def check_job_details_batch(
    results: object, urls: list[str], source: str, is_test: bool
) -> tuple[list[FetchedJobDetail], list[JobDetailExtractionLog]]:
    """The batch split into successes and failures, if valid; error otherwise."""
    if not isinstance(results, list):
        raise ContractViolationError(f"expected a list, got {type(results)}")
    fetched: list[FetchedJobDetail] = []
    failures: list[JobDetailExtractionLog] = []
    for result in results:
        if isinstance(result, FetchedJobDetail):
            _check_fetched(result)
            fetched.append(result)
        elif isinstance(result, JobDetailExtractionLog):
            failures.append(result)
        else:
            raise ContractViolationError(f"unexpected result {type(result)}")
    _check_urls([r.job_detail.url for r in fetched] + [f.url for f in failures], urls)
    for record in [r.job_detail for r in fetched] + failures:
        _check_origin(record.source, record.is_test, source, is_test)
    return fetched, failures


def _check_fetched(result: FetchedJobDetail) -> None:
    """The receipt describes exactly the content it comes with."""
    if result.job_detail.raw_hash != compute_raw_hash(result.content):
        raise ContractViolationError(f"raw_hash mismatch for {result.job_detail.url}")


def _check_urls(answered: list[str], asked: list[str]) -> None:
    """Exactly one result per URL asked."""
    if sorted(answered) != sorted(asked):
        raise ContractViolationError("expected exactly one result per URL asked")


def _check_origin(
    source: str, is_test: bool, expected_source: str, expected_is_test: bool
) -> None:
    """The record comes from this site and this kind of run."""
    if (source, is_test) != (expected_source, expected_is_test):
        raise ContractViolationError(
            f"record of ({source}, is_test={is_test}), "
            f"expected ({expected_source}, is_test={expected_is_test})"
        )
