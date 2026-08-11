from inkcre_extension_registry.contracts.models import ExtensionSummary
from inkcre_extension_registry.service.ui import extension_catalog_html


def test_catalog_escapes_publisher_owned_nickname() -> None:
    document = extension_catalog_html(
        [ExtensionSummary(name="inkcre/twitter", nickname="<script>alert('x')</script>")]
    )

    assert "<script>" not in document
    assert "&lt;script&gt;alert(&#x27;x&#x27;)&lt;/script&gt;" in document
    assert 'href="/v1/extensions/inkcre/twitter"' in document
