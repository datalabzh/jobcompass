"""
tables.py

Description : les tables écrites par la brique extraction.
Règles      : le stockage est partagé et ne connaît aucune table : chaque brique
              nomme les siennes. Le nom de la table = le nom de son dossier.
              Une table = un seul contrat.
"""

from enum import StrEnum


class Table(StrEnum):
    """The tables of the extraction brick, with their contract."""

    JOB_INFO = "job_info"  # JobInfo, one line per job seen per run
    JOB_INFO_EXTRACTION_LOG = "job_info_extraction_log"  # one line per category run
    JOB_DETAIL = "job_detail"  # JobDetail, one line per page downloaded
    JOB_DETAIL_EXTRACTION_LOG = "job_detail_extraction_log"  # one per failure
