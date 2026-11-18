"""
pydantic_to_json_schema.py

Description : exporte chaque contrat en fichier JSON Schema dans contracts/schemas/.
Règles      : les classes Pydantic font foi ; les fichiers JSON Schema sont générés,
              jamais écrits à la main.
              Nom du fichier = <contrat>.v<schema_version>.json.
              Usage : uv run python contracts/scripts/pydantic_to_json_schema.py
"""

import json
from pathlib import Path

from pydantic import BaseModel

from contracts import (
    LogRawJobDetail,
    LogRawJobInfo,
    NormalizedJob,
    RawJobDetail,
    RawJobInfo,
)

SCHEMAS_DIR: Path = Path(__file__).resolve().parents[1] / "schemas"
CONTRACTS: dict[str, type[BaseModel]] = {
    "raw_job_info": RawJobInfo,
    "log_raw_job_info": LogRawJobInfo,
    "raw_job_detail": RawJobDetail,
    "log_raw_job_detail": LogRawJobDetail,
    "normalized_job": NormalizedJob,
}


def main() -> None:
    """Write the JSON Schema of every contract into contracts/schemas/."""
    SCHEMAS_DIR.mkdir(exist_ok=True)
    for name, model in CONTRACTS.items():
        version: str = model.model_fields["schema_version"].default
        path: Path = SCHEMAS_DIR / f"{name}.v{version}.json"
        schema: dict[str, object] = model.model_json_schema()
        path.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n")
        print(f"written {path.name}")


if __name__ == "__main__":
    main()
