from pathlib import Path

import yaml


SPEC_PATH = (
    Path(__file__).resolve().parents[2]
    / "contracts"
    / "auth.openapi.yaml"
)


def test_openapi_schema_references_resolve():
    spec = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))

    def check_references(value):
        if isinstance(value, dict):
            if "$ref" in value:
                reference = value["$ref"]
                assert reference.startswith("#/")

                target = spec
                for part in reference[2:].split("/"):
                    key = part.replace("~1", "/").replace("~0", "~")
                    target = target[key]

            for child in value.values():
                check_references(child)

        elif isinstance(value, list):
            for child in value:
                check_references(child)

    check_references(spec)