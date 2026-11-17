"""
jobup_parser.py

Description : parseur de jobup.ch : lit le contenu des pages que JobupExtraction a
              téléchargées, sans jamais faire de requête ni rien écrire.
Règles      : une seule méthode publique, parse(kind, content) :
                'job_info'   page de résultats -> JobupListing
                'job_detail' fiche d'un job    -> JobupJobDetail
              Un autre parseur jobup (autre librairie...) = une nouvelle classe
              IParser qui renvoie ces mêmes types, déclarée dans le site.toml.
              Page de résultats : données dans le script `__INIT__ = {...}` :
                vacancy.results.main.meta     numPages, totalHits
                vacancy.results.main.results  les jobs de la page (cartes brutes)
              URL d'un job construite à partir de son id.
              Fiche : JSON-LD JobPosting ; valeurs telles que données par la source
              (aucune interprétation), description débarrassée du HTML, date de
              publication ramenée à un jour. Champ absent = None, ou liste vide.
              Contenu illisible (pas de __INIT__, pas de JobPosting) : ParsingError.
              Changer ce qui est lu ou comment = monter version.
"""

import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from html.parser import HTMLParser
from typing import Any

from interfaces import IParser, ParsingError

JOB_INFO: str = "job_info"  # a result page
JOB_DETAIL: str = "job_detail"  # the detail page of a job
JOB_URL: str = "https://www.jobup.ch/fr/emplois/detail/{id}/"
INIT_MARKER: str = "__INIT__"
JSON_LD: re.Pattern[str] = re.compile(
    r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', re.DOTALL
)
BLOCK_TAGS: frozenset[str] = frozenset(
    {"p", "div", "br", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "tr"}
)


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
    """What a job detail page says, in the fields common to every site."""

    title: str
    company: str | None
    description: str
    date_posted: date | None
    postal_code: str | None
    employment_types: list[str]
    categories: list[str]
    declared_skills: list[str]


class JobupParser(IParser):
    """Reads jobup.ch pages: result pages (__INIT__) and job details (JSON-LD)."""

    name: str = "jobup_parser"
    version: str = "1.0.0"

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
        """The fields of a job, read from its JSON-LD JobPosting."""
        posting: dict[str, Any] = self._job_posting(html)
        return JobupJobDetail(
            title=str(posting.get("title") or "").strip(),
            company=self._company(posting),
            description=self._html_to_text(str(posting.get("description") or "")),
            date_posted=self._date_posted(posting),
            postal_code=self._postal_code(posting),
            employment_types=self._texts(posting.get("employmentType")),
            categories=self._texts(posting.get("occupationalCategory")),
            declared_skills=self._texts(posting.get("skills")),
        )

    def _job_posting(self, html: str) -> dict[str, Any]:
        """The JobPosting object among the JSON-LD blocks of the page."""
        for block in JSON_LD.findall(html):
            try:
                data: Any = json.loads(block)
            except json.JSONDecodeError:
                continue
            for item in data if isinstance(data, list) else [data]:
                if isinstance(item, dict) and item.get("@type") == "JobPosting":
                    return item
        raise ParsingError("no JSON-LD JobPosting")

    def _company(self, posting: dict[str, Any]) -> str | None:
        """Name of the hiring organization, if given."""
        names: list[str] = self._texts(posting.get("hiringOrganization"))
        return names[0] if names else None

    def _date_posted(self, posting: dict[str, Any]) -> date | None:
        """Day of publication, if given and readable."""
        value: Any = posting.get("datePosted")
        if not isinstance(value, str) or not value:
            return None
        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            return None

    def _postal_code(self, posting: dict[str, Any]) -> str | None:
        """Postal code of the first job location, if given."""
        location: Any = posting.get("jobLocation")
        if isinstance(location, list):
            location = location[0] if location else None
        if not isinstance(location, dict):
            return None
        address: Any = location.get("address")
        if not isinstance(address, dict) or address.get("postalCode") is None:
            return None
        return str(address["postalCode"]).strip() or None

    def _texts(self, value: Any) -> list[str]:  # noqa: ANN401
        """Texts of a JSON-LD value: a text, an object (its name) or a list of them."""
        items: list[Any] = value if isinstance(value, list) else [value]
        texts: list[str] = []
        for item in items:
            text: Any = item.get("name") if isinstance(item, dict) else item
            if isinstance(text, str) and text.strip():
                texts.append(text.strip())
        return texts

    def _html_to_text(self, html: str) -> str:
        """The text of an HTML fragment, one line per block, spaces collapsed."""
        reader: _TextReader = _TextReader()
        reader.feed(html)
        reader.close()
        lines: list[str] = [
            " ".join(line.split()) for line in reader.text().split("\n")
        ]
        return "\n".join(line for line in lines if line)


class _TextReader(HTMLParser):
    """Collects the text of an HTML fragment, with a line break at each block."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """A block tag starts a new line."""
        if tag in BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        """A block tag ends its line."""
        if tag in BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        """Keep the text."""
        self._parts.append(data)

    def text(self) -> str:
        """All the text collected."""
        return "".join(self._parts)
