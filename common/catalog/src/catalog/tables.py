"""
tables.py

Description : le catalogue des tables de JobCompass : où sont rangées les données,
              pour toutes les briques (extraction, normalisation, SQL, Dagster).
Règles      : une table = un seul contrat ; le nom de la table = le nom de son
              dossier dans le stockage. Le stockage ne connaît aucune table : c'est
              ici qu'on les nomme, une seule fois pour tout le projet.
              Ajouter une table = ajouter une ligne, avec en commentaire le contrat
              qu'elle contient.
"""

from enum import StrEnum


class Table(StrEnum):
    """Every table of JobCompass, with the contract it holds."""

    # extraction
    RAW_JOB_INFO = "raw_job_info"  # RawJobInfo, one per job seen per run
    RAW_JOB_INFO_EXTRACTION_LOG = "raw_job_info_extraction_log"  # one per listing
    RAW_JOB_DETAIL = "raw_job_detail"  # RawJobDetail, one per page downloaded
    RAW_JOB_DETAIL_EXTRACTION_LOG = "raw_job_detail_extraction_log"  # one per failure
    RAW_JOB_DETAIL_HTML = "raw_job_detail_html"  # folder of the raw pages
