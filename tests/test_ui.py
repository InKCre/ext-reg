import pytest

from inkcre_extension_registry.contracts.models import ExtensionSummary
from inkcre_extension_registry.service.ui import extension_catalog_html


def test_catalog_escapes_publisher_owned_nickname() -> None:
    document = extension_catalog_html(
        [ExtensionSummary(name="inkcre/twitter", nickname="<script>alert('x')</script>")]
    )

    assert "<script>" not in document
    assert "&lt;script&gt;alert(&#x27;x&#x27;)&lt;/script&gt;" in document
    assert 'href="/v1/extensions/inkcre/twitter"' in document


def test_catalog_preview_uses_the_production_api_origin_and_noindex() -> None:
    document = extension_catalog_html(
        [ExtensionSummary(name="inkcre/twitter", nickname="Twitter")],
        api_origin="https://registry.inkcre.dev",
        noindex=True,
    )

    assert 'content="noindex,nofollow"' in document
    assert 'href="https://registry.inkcre.dev/v1/extensions/inkcre/twitter"' in document
    assert 'href="https://registry.inkcre.dev/v1/extensions"' in document


@pytest.mark.parametrize(
    "origin",
    [
        "http://registry.inkcre.dev",
        "https://registry.inkcre.dev/",
        "https://registry.inkcre.dev/path",
        "https://user@registry.inkcre.dev",
        "https://registry.inkcre.dev?query=yes",
    ],
)
def test_catalog_preview_rejects_noncanonical_api_origins(origin: str) -> None:
    with pytest.raises(ValueError, match="canonical absolute HTTPS origin"):
        extension_catalog_html([], api_origin=origin)


def test_catalog_empty_state_and_production_defaults_remain_stable() -> None:
    document = extension_catalog_html([])

    assert "No Extensions published yet." in document
    assert 'name="robots"' not in document
    assert 'href="/v1/extensions"' in document
