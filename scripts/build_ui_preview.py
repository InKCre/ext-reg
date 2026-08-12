from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

from inkcre_extension_registry.contracts.models import ExtensionSummary
from inkcre_extension_registry.service.ui import extension_catalog_html

MAX_DOCUMENT_BYTES = 64 * 1024


class PreviewFixture(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1]
    extensions: tuple[ExtensionSummary, ...]

    @field_validator("extensions")
    @classmethod
    def extension_names_are_unique(
        cls, extensions: tuple[ExtensionSummary, ...]
    ) -> tuple[ExtensionSummary, ...]:
        names = [extension.name for extension in extensions]
        if len(names) != len(set(names)):
            raise ValueError("extension names must be unique")
        return extensions


def build_preview(*, fixture_path: Path, output_directory: Path, api_origin: str) -> Path:
    fixture = PreviewFixture.model_validate_json(fixture_path.read_bytes())
    if output_directory.exists() and any(output_directory.iterdir()):
        raise ValueError("output directory must be empty")
    output_directory.mkdir(parents=True, exist_ok=True)

    document = extension_catalog_html(
        fixture.extensions,
        api_origin=api_origin,
        noindex=True,
    ).encode()
    if len(document) > MAX_DOCUMENT_BYTES:
        raise ValueError(f"preview document exceeds {MAX_DOCUMENT_BYTES} bytes")

    output = output_directory / "index.html"
    output.write_bytes(document)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the static Extension-list PR preview")
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--api-origin", required=True)
    arguments = parser.parse_args()

    output = build_preview(
        fixture_path=arguments.fixture,
        output_directory=arguments.output,
        api_origin=arguments.api_origin,
    )
    print(
        json.dumps(
            {"document": str(output), "size": output.stat().st_size},
            separators=(",", ":"),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
