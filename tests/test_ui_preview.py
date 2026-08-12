from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

FIXTURE = Path("tests/fixtures/ui-preview.json")
BUILDER = Path("scripts/build_ui_preview.py")


def run_builder(*, fixture: Path, output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--fixture",
            str(fixture),
            "--output",
            str(output),
            "--api-origin",
            "https://registry.inkcre.dev",
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def test_preview_fixture_and_document_are_deterministic(tmp_path: Path) -> None:
    first_run = run_builder(fixture=FIXTURE, output=tmp_path / "first")
    second_run = run_builder(fixture=FIXTURE, output=tmp_path / "second")
    assert first_run.returncode == 0, first_run.stderr
    assert second_run.returncode == 0, second_run.stderr
    first = tmp_path / "first/index.html"
    second = tmp_path / "second/index.html"

    assert first.read_bytes() == second.read_bytes()
    assert first.stat().st_size <= 64 * 1024
    assert [path.name for path in first.parent.iterdir()] == ["index.html"]
    document = first.read_text()
    assert document.count('class="extension"') == 6
    assert "https://registry.inkcre.dev/v1/extensions/inkcre/twitter" in document
    assert 'content="noindex,nofollow"' in document


def test_preview_fixture_rejects_duplicate_and_unknown_data(tmp_path: Path) -> None:
    duplicate = {
        "schema_version": 1,
        "extensions": [
            {"name": "inkcre/twitter", "nickname": "Twitter"},
            {"name": "inkcre/twitter", "nickname": "Duplicate"},
        ],
    }
    duplicate_path = tmp_path / "duplicate.json"
    duplicate_path.write_text(json.dumps(duplicate))
    duplicate_run = run_builder(fixture=duplicate_path, output=tmp_path / "duplicate")
    assert duplicate_run.returncode != 0
    assert "extension names must be unique" in duplicate_run.stderr

    extra_path = tmp_path / "extra.json"
    extra_path.write_text(json.dumps(duplicate | {"unexpected": True}))
    extra_run = run_builder(fixture=extra_path, output=tmp_path / "extra")
    assert extra_run.returncode != 0
    assert "Extra inputs are not permitted" in extra_run.stderr


def test_preview_builder_rejects_nonempty_output_directory(tmp_path: Path) -> None:
    output = tmp_path / "preview"
    output.mkdir()
    (output / "existing.txt").write_text("do not overwrite")

    result = run_builder(fixture=FIXTURE, output=output)

    assert result.returncode != 0
    assert "output directory must be empty" in result.stderr


def test_checked_fixture_has_the_expected_review_catalog() -> None:
    fixture = json.loads(FIXTURE.read_text())

    assert fixture["schema_version"] == 1
    assert [extension["name"] for extension in fixture["extensions"]] == [
        "inkcre/github",
        "inkcre/learn-english",
        "inkcre/mail",
        "inkcre/rss",
        "inkcre/telegram",
        "inkcre/twitter",
    ]
