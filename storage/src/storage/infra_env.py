"""
infra_env.py

Description : emplacement du fichier de variables de l'infrastructure locale
              (infra/.env), lu par les stockages pour se connecter aux conteneurs.
Règles      : chemin relatif à la racine du dépôt, déduit de l'emplacement de ce
              fichier : il ne dépend pas du dossier d'où l'on lance la commande.
              Une variable d'environnement définie l'emporte sur le fichier.
"""

from pathlib import Path

REPO_ROOT: Path = Path(__file__).resolve().parents[3]
INFRA_ENV_FILE: Path = REPO_ROOT / "infra" / ".env"
