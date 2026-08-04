"""Export CarbonEvidenceRegistry ABI from Foundry artifacts to the Python service."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT = (
    ROOT / "contracts" / "out" / "CarbonEvidenceRegistry.sol" / "CarbonEvidenceRegistry.json"
)
DEFAULT_OUT = (
    ROOT
    / "app"
    / "infrastructure"
    / "anchoring"
    / "contracts"
    / "CarbonEvidenceRegistry.abi.json"
)


def export_abi(artifact_path: Path, output_path: Path) -> dict:
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    abi = artifact.get("abi")
    if not isinstance(abi, list):
        raise ValueError(f"ABI missing in artifact: {artifact_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(abi, indent=2) + "\n", encoding="utf-8")
    return {"abi_entries": len(abi), "output": str(output_path)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Export contract ABI for Python")
    parser.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    if not args.artifact.exists():
        raise SystemExit(f"Artifact not found. Run forge build first: {args.artifact}")
    result = export_abi(args.artifact, args.output)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
