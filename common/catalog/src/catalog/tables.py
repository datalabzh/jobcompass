"""
tables.py

Description : le catalogue des tables de JobCompass : où sont rangées les données,
              pour toutes les briques (extraction, normalisation, SQL, Dagster).
Règles      : une table = un seul contrat ; le nom de la table = le nom de son
              dossier dans le stockage. Le stockage ne connaît aucune table : c'est
              ici qu'on les nomme, une seule fois pour tout le projet.
              Ajouter une table = ajouter une ligne, avec en commentaire le contrat
              qu'elle contient.
              Journaux : log_ + nom de la table qu'ils accompagnent (ex.
              log_raw_job_detail), pour qu'ils se rangent ensemble.
"""

from enum import StrEnum


class Table(StrEnum):
    """Every table of JobCompass, with the contract it holds."""

    # extraction
    RAW_JOB_INFO = "raw_job_info"  # RawJobInfo, one per job seen per run
    LOG_RAW_JOB_INFO = "log_raw_job_info"  # LogRawJobInfo, one per listing
    RAW_JOB_DETAIL = "raw_job_detail"  # RawJobDetail, one per page downloaded
    LOG_RAW_JOB_DETAIL = "log_raw_job_detail"  # LogRawJobDetail, one per failure
    RAW_JOB_DETAIL_HTML = "raw_job_detail_html"  # folder of the raw pages
    EXTRACTED_JOB = "extracted_job"  # ExtractedJob, one per page parsed
    LOG_EXTRACTED_JOB = "log_extracted_job"  # LogExtractedJob, one per failure

    # normalization
    NORMALIZED_JOB = "normalized_job"  # NormalizedJob, one per job normalized
