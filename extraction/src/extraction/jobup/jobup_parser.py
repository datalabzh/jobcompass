"""
jobup_parser.py

Description : parseur de jobup.ch : lit le contenu des pages que
              JobupExtractionUseCase a téléchargées, sans jamais faire de requête
              ni rien écrire.
Règles      : une seule méthode publique, parse(kind, content) :
                'job_info'   page de résultats -> JobupListing
                'job_detail' fiche d'un job    -> JobupJobDetail
              Utilisé directement par JobupExtractionUseCase : sa version n'est pas
              enregistrée seule ; changer ce qui est lu ou comment = monter aussi
              JobupExtractionUseCase.version (enregistrée avec chaque page).
              Page de résultats : données dans le script `__INIT__ = {...}` :
                vacancy.results.main.meta     numPages, totalHits
                vacancy.results.main.results  les jobs de la page (cartes brutes)
              URL d'un job construite à partir de son id. Page sans __INIT__ :
              ParsingError.
              Fiche (ADR-0002 : aucun champ choisi ni renommé, c'est le travail de
              dbt), lue avec selectolax : le bloc JSON-LD qui contient le
              JobPosting, texte exact de la page (json_ld) ; à défaut, les
              paragraphes du texte visible (sans script ni style), un par bloc
              HTML, dans l'ordre, en liste JSON (paragraphs). Une fiche est donc
              toujours lue.
"""

import json
from dataclasses import dataclass
from typing import Any

from selectolax.lexbor import LexborHTMLParser

from contracts import PayloadFormat
from extraction.interfaces import IParser, ParsingError

JOB_INFO: str = "job_info"  # a result page
JOB_DETAIL: str = "job_detail"  # the detail page of a job
JOB_URL: str = "https://www.jobup.ch/fr/emplois/detail/{id}/"
INIT_MARKER: str = "__INIT__"
JSON_LD: str = 'script[type^="application/ld+json"]'  # also '...; charset=...'
BLOCKS: str = "p, div, br, li, ul, ol, h1, h2, h3, h4, h5, h6, tr"
HIDDEN_TAGS: list[str] = ["script", "style", "noscript", "template"]


@dataclass(frozen=True)
class JobupJobInfo:
    """One job of a result page: its URL and its card as given by jobup."""

    url: str
    card: dict[str, Any]


@dataclass(frozen=True)
class JobupListing:
    """One result page: its jobs, and the counts of the category."""

    num_pages: int
    total: int | None
    jobs: list[JobupJobInfo]


@dataclass(frozen=True)
class JobupJobDetail:
    """The raw data block of a job detail page, as JSON text."""

    payload_format: PayloadFormat
    payload: str


class JobupParser(IParser):
    """Reads jobup.ch pages: result pages (__INIT__) and job details (raw block)."""

    name: str = "jobup_parser"
    version: str = "2.0.0"

    def parse(self, kind: str, content: bytes) -> JobupListing | JobupJobDetail:
        """What a page of this kind holds; ParsingError if it cannot be read."""
        html: str = content.decode("utf-8", "replace")
        if kind == JOB_INFO:
            return self._parse_job_info(html)
        if kind == JOB_DETAIL:
            return self._parse_job_detail(html)
        raise ValueError(f"unknown page kind '{kind}'")

    # --- result pages -----------------------------------------------------------

    def _parse_job_info(self, html: str) -> JobupListing:
        """The jobs of a result page, the page count and the announced total."""
        data: dict[str, Any] = self._init_data(html)
        try:
            return JobupListing(
                num_pages=int(data["meta"]["numPages"]),
                total=data["meta"].get("totalHits"),
                jobs=[
                    JobupJobInfo(url=JOB_URL.format(id=job["id"]), card=job)
                    for job in data["results"]
                ],
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ParsingError(f"unexpected __INIT__ content: {error!r}") from error

    def _init_data(self, html: str) -> dict[str, Any]:
        """vacancy.results.main, from the __INIT__ JSON of the page."""
        start: int = html.find(INIT_MARKER)
        if start == -1:
            raise ParsingError("no __INIT__ block")
        try:
            init: dict[str, Any]
            init, _ = json.JSONDecoder().raw_decode(html, html.index("{", start))
            return init["vacancy"]["results"]["main"]
        except (KeyError, TypeError, ValueError) as error:
            raise ParsingError(f"unreadable __INIT__ block: {error!r}") from error

    # --- job details ------------------------------------------------------------

    def _parse_job_detail(self, html: str) -> JobupJobDetail:
        """The JSON-LD block of the JobPosting, or else the paragraphs of the page."""
        tree: LexborHTMLParser = LexborHTMLParser(html)
        block: str | None = self._job_posting_block(tree)
        if block is not None:
            return JobupJobDetail(payload_format=PayloadFormat.JSON_LD, payload=block)
        return JobupJobDetail(
            payload_format=PayloadFormat.PARAGRAPHS,
            payload=json.dumps(self._paragraphs(tree), ensure_ascii=False),
        )

    def _job_posting_block(self, tree: LexborHTMLParser) -> str | None:
        """The text of the JSON-LD block holding a JobPosting, as in the page."""
        for node in tree.css(JSON_LD):
            block: str = node.text()
            try:
                data: Any = json.loads(block)
            except json.JSONDecodeError:
                continue
            for item in data if isinstance(data, list) else [data]:
                if isinstance(item, dict) and item.get("@type") == "JobPosting":
                    return block.strip()
        return None

    def _paragraphs(self, tree: LexborHTMLParser) -> list[str]:
        """The visible text of the page, one paragraph per block, spaces collapsed."""
        tree.strip_tags(HIDDEN_TAGS)
        for node in tree.css(BLOCKS):
            node.insert_before("\n")
            node.insert_after("\n")
        text: str = tree.body.text() if tree.body is not None else ""
        lines: list[str] = [" ".join(line.split()) for line in text.split("\n")]
        return [line for line in lines if line]
