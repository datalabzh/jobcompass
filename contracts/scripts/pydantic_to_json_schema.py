"""
pydantic_to_json_schema.py

Description : exports every contract as a JSON Schema file into contracts/schemas/.
Rules       : the Pydantic classes are the source of truth, the JSON Schema files
              are generated, never written by hand.
              File name = <contract>.v<schema_version>.json.
              Usage: uv run python contracts/scripts/pydantic_to_json_schema.py
"""

import json
from pathlib import Path

from pydantic import BaseModel

from contracts import (
    JobDetail,
    JobDetailExtractionLog,
    JobInfo,
    JobInfoExtractionLog,
)

SCHEMAS_DIR: Path = Path(__file__).resolve().parents[1] / "schemas"
CONTRACTS: dict[str, type[BaseModel]] = {
    "job_info": JobInfo,
    "job_info_extraction_log": JobInfoExtractionLog,
    "job_detail": JobDetail,
    "job_detail_extraction_log": JobDetailExtractionLog,
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
