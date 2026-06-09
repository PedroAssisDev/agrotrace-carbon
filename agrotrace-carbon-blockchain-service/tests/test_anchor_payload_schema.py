import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT_DIR = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT_DIR / "schemas" / "anchor_payload.schema.json"
PRIVATE_EXAMPLE_PATH = ROOT_DIR / "data" / "examples" / "anchor_payload_private.example.json"
PUBLIC_EXAMPLE_PATH = ROOT_DIR / "data" / "examples" / "anchor_payload_public_summary.example.json"


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file_obj:
        return json.load(file_obj)


class TestAnchorPayloadSchema(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        schema = _load_json(SCHEMA_PATH)
        cls.validator = Draft202012Validator(schema)
        cls.private_example = _load_json(PRIVATE_EXAMPLE_PATH)
        cls.public_example = _load_json(PUBLIC_EXAMPLE_PATH)

    def assert_valid(self, payload: dict) -> None:
        errors = list(self.validator.iter_errors(payload))
        if errors:
            first_error = errors[0]
            self.fail(
                f"Payload should be valid but failed: {first_error.message} "
                f"(path: {'/'.join(map(str, first_error.path))})"
            )

    def assert_invalid(self, payload: dict) -> None:
        errors = list(self.validator.iter_errors(payload))
        self.assertGreater(len(errors), 0, "Payload should be invalid but passed validation.")

    def test_private_example_is_valid(self) -> None:
        self.assert_valid(self.private_example)

    def test_public_summary_example_is_valid(self) -> None:
        self.assert_valid(self.public_example)

    def test_payload_without_package_hash_is_invalid(self) -> None:
        payload = copy.deepcopy(self.private_example)
        payload["integrity"].pop("package_hash", None)
        self.assert_invalid(payload)

    def test_public_summary_enabled_without_total_emission_is_invalid(self) -> None:
        payload = copy.deepcopy(self.public_example)
        payload["public_summary"]["enabled"] = True
        payload["public_summary"].pop("total_emission_scaled", None)
        self.assert_invalid(payload)

    def test_unknown_package_type_is_invalid(self) -> None:
        payload = copy.deepcopy(self.private_example)
        payload["evidence_package"]["package_type"] = "unknown_package_type"
        self.assert_invalid(payload)

    def test_unknown_period_granularity_is_invalid(self) -> None:
        payload = copy.deepcopy(self.private_example)
        payload["evidence_package"]["period"]["period_granularity"] = "biweekly"
        self.assert_invalid(payload)


if __name__ == "__main__":
    unittest.main()
