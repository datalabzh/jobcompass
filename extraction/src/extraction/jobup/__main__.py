"""
__main__.py

Description : lance l'extraction de jobup depuis son dossier, pendant le
              développement : python -m extraction.jobup [--max-pages N] ...
Règles      : exactement le même chemin que Dagster : appelle le point d'entrée
              unique avec le site 'jobup', les autres options passent telles quelles.
"""

import sys

from extraction.cli import main

if __name__ == "__main__":
    sys.exit(main(["run", "jobup", *sys.argv[1:]]))
