"""
jobup_job_details.py

Description : job details de jobup.ch : la page de détail brute de chaque job.
Règles      : cas courant, sans particularité : toute réponse 2xx est conservée
              telle quelle (_download_detail de l'interface).
              Changer la façon de télécharger = monter version.
"""

from extraction.interfaces.i_job_details_extractor import (
    IJobDetailsExtractor,
    JobDetailResult,
)


class JobupJobDetails(IJobDetailsExtractor):
    """Downloads jobup.ch job detail pages."""

    version: str = "0.1.0"

    def execute(self, urls: list[str]) -> list[JobDetailResult]:
        """One result per URL: the fetched page, or the reason of the failure."""
        return [self._download_detail(url) for url in urls]
