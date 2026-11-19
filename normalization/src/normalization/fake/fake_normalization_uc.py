"""
fake_normalization_uc.py

Description : normalisation factice : produit des compétences plausibles sans NLP,
              pour faire tourner toute la chaîne en attendant le vrai normaliseur
              de l'équipe NLP.
Règles      : compétences déclarées par la source (declared_skills) : gardées,
              origine 'declared', forme canonique = forme brute en minuscules.
              Compétences détectées : recherche, dans le titre et la description,
              des mots d'une petite liste fixe de technos (KEYWORDS), sans tenir
              compte de la casse ; origine 'detected', forme brute = le texte trouvé.
              Une compétence n'apparaît qu'une fois par job (la déclarée l'emporte).
              Jobs à normaliser = jobs extraits - déjà normalisés par cette classe
              (mêmes noms et versions) ; au plus max_jobs, un par un, chacun écrit
              dès qu'il est traité.
              Changer la liste ou la détection = monter model_version.
              Réglages : fake/normalizer.toml.
"""

import re
from typing import Any

from catalog import Table
from contracts import NormalizedJob, NormalizedSkill, SkillOrigin
from normalization.interfaces import INormalizationUseCase, NormalizationReport

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


class FakeNormalizationUseCase(INormalizationUseCase):
    """Fake skills: the declared ones, plus fixed keywords found in the text."""

    normalizer: str = "fake_normalization"
    normalizer_version: str = "0.1.0"
    model: str = "keyword_list"
    model_version: str = "0.1.0"
    description: str = (
        "Fake skills to test the pipeline: the skills declared by the source, plus"
        " about thirty fixed technology keywords found in the title and description."
    )

    def execute(self) -> NormalizationReport:
        """Normalize the pending extracted jobs one by one."""
        pending: list[dict[str, Any]] = self._pending_jobs()
        selected: list[dict[str, Any]] = pending[: self.max_jobs]
        for job in selected:
            self.storage.append(Table.NORMALIZED_JOB, [self._normalize(job)])
        return NormalizationReport(
            source=self.source,
            is_test=self.is_test,
            max_jobs=self.max_jobs,
            normalized=len(selected),
            remaining=len(pending) - len(selected),
        )

    def _pending_jobs(self) -> list[dict[str, Any]]:
        """Extracted jobs not normalized yet by this class, oldest first."""
        done: set[tuple[str, str]] = {
            (row["raw_hash"], row["parser_version"])
            for row in self.storage.read(Table.NORMALIZED_JOB, self.source)
            if (
                row["normalizer"],
                row["normalizer_version"],
                row["model"],
                row["model_version"],
            )
            == (
                self.normalizer,
                self.normalizer_version,
                self.model,
                self.model_version,
            )
        }
        extracted: list[dict[str, Any]] = sorted(
            self.storage.read(Table.EXTRACTED_JOB, self.source),
            key=lambda row: row["parsed_at"],
        )
        return [
            row
            for row in extracted
            if (row["raw_hash"], row["parser_version"]) not in done
        ]

    def _normalize(self, job: dict[str, Any]) -> NormalizedJob:
        """The NormalizedJob of one extracted job."""
        return NormalizedJob(
            source=self.source,
            is_test=self.is_test,
            url=job["url"],
            raw_hash=job["raw_hash"],
            parser_version=job["parser_version"],
            normalizer=self.normalizer,
            normalizer_version=self.normalizer_version,
            model=self.model,
            model_version=self.model_version,
            normalizer_description=self.description,
            normalized_at=self.now(),
            skills=self._skills(job),
        )

    def _skills(self, job: dict[str, Any]) -> list[NormalizedSkill]:
        """Declared skills first, then the keywords found in title and text."""
        skills: dict[str, NormalizedSkill] = {}
        for raw in job["declared_skills"]:
            canonical: str = raw.strip().lower()
            skills.setdefault(
                canonical,
                NormalizedSkill(
                    raw=raw, canonical=canonical, origin=SkillOrigin.DECLARED
                ),
            )
        text: str = f"{job['title']}\n{job['description']}"
        for canonical, pattern in PATTERNS.items():
            found: re.Match[str] | None = pattern.search(text)
            if found is not None and canonical not in skills:
                skills[canonical] = NormalizedSkill(
                    raw=found.group(0), canonical=canonical, origin=SkillOrigin.DETECTED
                )
        return list(skills.values())
