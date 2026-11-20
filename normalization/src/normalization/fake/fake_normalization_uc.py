"""
fake_normalization_uc.py

Description : normalisation factice : produit des compétences plausibles sans NLP,
              pour faire tourner toute la chaîne en attendant le vrai normaliseur
              de l'équipe NLP. Normaliseur courant au démarrage (config.normalizer).
Règles      : entrée = raw_job_detail ; le payload est analysé ici, selon son
              format :
                json_ld    : texte = title + description ; compétences déclarées =
                             la clé skills (liste, ou texte séparé par des virgules) ;
                paragraphs : texte = les paragraphes ; aucune compétence déclarée.
              Compétences déclarées : gardées, origine 'declared', forme canonique =
              forme brute en minuscules.
              Compétences détectées : recherche, dans le texte, des mots d'une petite
              liste fixe de technos (KEYWORDS), sans tenir compte de la casse ;
              origine 'detected', forme brute = le texte trouvé.
              Une compétence n'apparaît qu'une fois par job (la déclarée l'emporte).
              Sortie : hash_html_id, scraper et scraper_version recopiés tels quels.
              Pages à normaliser = lignes de raw_job_detail - déjà normalisées par
              cette classe (mêmes noms et versions), de la plus ancienne à la plus
              récente ; au plus max_jobs, une par une, chacune écrite dès qu'elle est
              traitée.
              Changer la liste ou la détection = monter model_version ; changer
              l'entrée ou la sortie = monter normalizer_version (et config.normalizer).
              Réglages : fake/normalizer.toml.
"""

import re
from typing import Any

from catalog.tables import Table
from contracts.components.field_types import PayloadFormat, SkillOrigin
from contracts.jobs.normalized_job import NormalizedJob, NormalizedSkill
from normalization.interfaces.i_normalization_uc import (
    INormalizationUseCase,
    NormalizationReport,
)

# canonical form -> what it looks like in a text (regular expression)
KEYWORDS: dict[str, str] = {
    "python": r"python",
    "java": r"java(?!\s*script)",
    "javascript": r"javascript|js",
    "typescript": r"typescript",
    "c#": r"c#",
    ".net": r"\.net",
    "php": r"php",
    "sql": r"sql",
    "postgresql": r"postgres(?:ql)?",
    "oracle": r"oracle",
    "sap": r"sap",
    "aws": r"aws",
    "azure": r"azure",
    "gcp": r"gcp|google cloud",
    "docker": r"docker",
    "kubernetes": r"kubernetes|k8s",
    "terraform": r"terraform",
    "linux": r"linux",
    "git": r"git",
    "ci/cd": r"ci\s*/\s*cd",
    "react": r"react",
    "angular": r"angular",
    "spark": r"spark",
    "airflow": r"airflow",
    "dbt": r"dbt",
    "power bi": r"power\s*bi",
    "excel": r"excel",
    "machine learning": r"machine learning",
    "scrum": r"scrum",
    "itil": r"itil",
}
PATTERNS: dict[str, re.Pattern[str]] = {
    canonical: re.compile(rf"(?<![\w.#+])(?:{pattern})(?![\w#+])", re.IGNORECASE)
    for canonical, pattern in KEYWORDS.items()
}
SIGNATURE_COLUMNS: list[str] = [
    "hash_html_id",
    "scraper",
    "scraper_version",
    "normalizer",
    "normalizer_version",
    "model",
    "model_version",
]
INPUT_COLUMNS: list[str] = [
    "hash_html_id",
    "scraper",
    "scraper_version",
    "fetched_at",
    "payload_format",
    "payload",
]


class FakeNormalizationUseCase(INormalizationUseCase):
    """Fake skills: the declared ones, plus fixed keywords found in the text."""

    normalizer: str = "fake_normalization"
    normalizer_version: str = "0.2.0"
    model: str = "keyword_list"
    model_version: str = "0.1.0"
    description: str = (
        "Fake skills to test the pipeline: the skills declared by the source, plus"
        " about thirty fixed technology keywords found in the title and description."
    )

    def execute(self) -> NormalizationReport:
        """Normalize the pending job detail pages one by one."""
        pending: list[dict[str, Any]] = self._pending_details()
        selected: list[dict[str, Any]] = pending[: self.max_jobs]
        for detail in selected:
            self.db_storage.append(Table.NORMALIZED_JOB, [self._normalize(detail)])
        return NormalizationReport(
            source=self.source,
            is_test=self.is_test,
            max_jobs=self.max_jobs,
            normalized=len(selected),
            remaining=len(pending) - len(selected),
        )

    def _pending_details(self) -> list[dict[str, Any]]:
        """Pages not normalized yet by this class, oldest first."""
        done: set[tuple[str, str, str]] = {
            (row["hash_html_id"], row["scraper"], row["scraper_version"])
            for row in self.db_storage.read(
                Table.NORMALIZED_JOB, self.source, columns=SIGNATURE_COLUMNS
            )
            if self._is_mine(row)
        }
        details: list[dict[str, Any]] = sorted(
            self.db_storage.read(
                Table.RAW_JOB_DETAIL, self.source, columns=INPUT_COLUMNS
            ),
            key=lambda row: row["fetched_at"],
        )
        return [
            row
            for row in details
            if (row["hash_html_id"], row["scraper"], row["scraper_version"]) not in done
        ]

    def _is_mine(self, row: dict[str, Any]) -> bool:
        """True if a normalized_job line was written by this class and versions."""
        return (
            row["normalizer"],
            row["normalizer_version"],
            row["model"],
            row["model_version"],
        ) == (self.normalizer, self.normalizer_version, self.model, self.model_version)

    def _normalize(self, detail: dict[str, Any]) -> NormalizedJob:
        """The NormalizedJob of one job detail page."""
        return NormalizedJob(
            source=self.source,
            is_test=self.is_test,
            hash_html_id=detail["hash_html_id"],
            scraper=detail["scraper"],
            scraper_version=detail["scraper_version"],
            normalizer=self.normalizer,
            normalizer_version=self.normalizer_version,
            model=self.model,
            model_version=self.model_version,
            normalizer_description=self.description,
            normalized_at=self.now(),
            skills=self._skills(detail),
        )

    def _skills(self, detail: dict[str, Any]) -> list[NormalizedSkill]:
        """Declared skills first, then the keywords found in the text."""
        skills: dict[str, NormalizedSkill] = {}
        for raw in self._declared_skills(detail):
            canonical: str = raw.lower()
            skills.setdefault(
                canonical,
                NormalizedSkill(
                    raw=raw, canonical=canonical, origin=SkillOrigin.DECLARED
                ),
            )
        text: str = self._text(detail)
        for canonical, pattern in PATTERNS.items():
            found: re.Match[str] | None = pattern.search(text)
            if found is not None and canonical not in skills:
                skills[canonical] = NormalizedSkill(
                    raw=found.group(0), canonical=canonical, origin=SkillOrigin.DETECTED
                )
        return list(skills.values())

    def _declared_skills(self, detail: dict[str, Any]) -> list[str]:
        """The skills key of a JSON-LD payload, as a list; none for paragraphs."""
        if detail["payload_format"] != PayloadFormat.JSON_LD:
            return []
        declared: Any = detail["payload"].get("skills") or []
        items: list[Any] = (
            declared.split(",") if isinstance(declared, str) else declared
        )
        return [str(item).strip() for item in items if str(item).strip()]

    def _text(self, detail: dict[str, Any]) -> str:
        """The text to search: JSON-LD title and description, or the paragraphs."""
        payload: Any = detail["payload"]
        if detail["payload_format"] == PayloadFormat.JSON_LD:
            return f"{payload.get('title', '')}\n{payload.get('description', '')}"
        return "\n".join(str(paragraph) for paragraph in payload)
