from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Literal

from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel, ConfigDict, field_validator

from inkcre_extension_registry.contracts.models import ExtensionRecord, ExtensionSummary
from inkcre_extension_registry.service.ui import (
    STYLES,
    extension_catalog_html,
    extension_detail_html,
)

MAX_DOCUMENT_BYTES = 64 * 1024


class PreviewFixture(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1]
    extensions: tuple[ExtensionRecord, ...]

    @field_validator("extensions")
    @classmethod
    def releases_match_extensions(
        cls, extensions: tuple[ExtensionRecord, ...]
    ) -> tuple[ExtensionRecord, ...]:
        names = [extension.name for extension in extensions]
        if len(names) != len(set(names)):
            raise ValueError("extension names must be unique")
        for extension in extensions:
            if not extension.releases or any(
                release.name != extension.name or release.state != "published"
                for release in extension.releases
            ):
                raise ValueError("preview details must be published releases of their extension")
            versions = [release.version for release in extension.releases]
            if len(versions) != len(set(versions)):
                raise ValueError("preview release versions must be unique")
        return extensions


def build_preview(*, fixture_path: Path, output_directory: Path) -> Path:
    fixture = PreviewFixture.model_validate_json(fixture_path.read_bytes())
    if output_directory.exists() and any(output_directory.iterdir()):
        raise ValueError("output directory must be empty")
    output_directory.mkdir(parents=True, exist_ok=True)

    documents = [
        (
            "Catalog",
            extension_catalog_html(
                [
                    ExtensionSummary(name=item.name, nickname=item.nickname)
                    for item in fixture.extensions
                ]
            ),
        )
    ]
    for extension in fixture.extensions:
        detail = extension_detail_html(extension)
        assert detail is not None  # The fixture requires published releases.
        documents.append((extension.nickname, detail))

    samples = []
    for index, (label, document) in enumerate(documents):
        body = document.split("<body>", 1)[1].split("</body>", 1)[0]
        # Each inert sample keeps the product's links and controls intact. Only
        # IDs are namespaced so independent documents can share the evidence page.
        body = re.sub(r' id="([^"]+)"', rf' id="sample-{index}-\1"', body)
        samples.append({"label": label, "body": body})
    templates = Environment(
        loader=FileSystemLoader(Path(__file__).parent / "templates"),
        autoescape=select_autoescape(["html"]),
    )
    document = (
        templates.get_template("ui-snapshots.html").render(styles=STYLES, samples=samples).encode()
    )
    if len(document) > MAX_DOCUMENT_BYTES:
        raise ValueError(f"preview document exceeds {MAX_DOCUMENT_BYTES} bytes")

    output = output_directory / "index.html"
    output.write_bytes(document)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build static samples of the Registry product pages"
    )
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    # Accept the old default-branch controller's argument until it is updated.
    parser.add_argument("--api-origin", help=argparse.SUPPRESS)
    arguments = parser.parse_args()

    output = build_preview(
        fixture_path=arguments.fixture,
        output_directory=arguments.output,
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
