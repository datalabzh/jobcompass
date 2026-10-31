"""Export every contract as a JSON Schema file into contracts/schemas/.

Usage: uv run python contracts/scripts/export_schemas.py
"""

import json
from pathlib import Path

from jobcompass_contracts import DiscoveredOffer, RawOffer

SCHEMAS_DIR = Path(__file__).resolve().parents[1] / "schemas"
CONTRACTS = {"discovered_offer": DiscoveredOffer, "raw_offer": RawOffer}


def main() -> None:
    SCHEMAS_DIR.mkdir(exist_ok=True)
    for name, model in CONTRACTS.items():
        version = model.model_fields["schema_version"].default
        path = SCHEMAS_DIR / f"{name}.v{version}.json"
        schema = model.model_json_schema()
        path.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n")
        print(f"written {path.name}")


if __name__ == "__main__":
    main()
