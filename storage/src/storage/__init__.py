"""
__init__.py

Description : stockage partagé par les briques JobCompass : ses interfaces
              (storage/interfaces) et ses implémentations, un fichier chacune.
Règles      : volontairement vide : on importe chaque classe par son chemin
              (from storage.s3_file_storage import S3FileStorage), et les TOML la
              désignent de même ("storage.s3_file_storage:S3FileStorage").
              Importer une interface ne charge ainsi aucune implémentation.
"""
