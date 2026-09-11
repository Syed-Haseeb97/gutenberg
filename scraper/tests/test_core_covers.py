import io
import zipfile

import pymupdf

from gutenberg2zim.core.covers import (
    extract_cover,
    extract_epub_cover,
    extract_pdf_cover,
)


def _epub(
    *,
    manifest: str,
    files: dict[str, bytes],
    metadata: str = "",
    opf_path: str = "OPS/package.opf",
) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr(
            "META-INF/container.xml",
            f'<container><rootfiles><rootfile full-path="{opf_path}"/>'
            "</rootfiles></container>",
        )
        archive.writestr(
            opf_path,
            f"<package><metadata>{metadata}</metadata><manifest>{manifest}"
            "</manifest></package>",
        )
        for path, content in files.items():
            archive.writestr(path, content)
    return output.getvalue()


def test_extract_pdf_cover_returns_first_page_image_bytes():
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "Cover")
    content = document.tobytes()
    document.close()

    cover = extract_pdf_cover(content)

    assert cover is not None
    assert cover.startswith(b"\x89PNG\r\n\x1a\n")


def test_extract_pdf_cover_returns_none_for_empty_pdf():
    assert extract_pdf_cover(b"") is None


def test_extract_epub_cover_uses_metadata_cover_from_nested_opf():
    epub = _epub(
        metadata='<meta name="cover" content="cover"/>',
        manifest=(
            '<item id="cover" href="images/cover%20image.jpg" '
            'media-type="image/jpeg"/>'
        ),
        files={"OPS/images/cover image.jpg": b"metadata cover"},
    )

    assert extract_epub_cover(epub) == b"metadata cover"


def test_extract_epub_cover_uses_cover_image_property():
    epub = _epub(
        manifest=(
            '<item id="cover" href="cover.jpg" media-type="image/jpeg" '
            'properties="cover-image"/>'
        ),
        files={"OPS/cover.jpg": b"property cover"},
    )

    assert extract_epub_cover(epub) == b"property cover"


def test_extract_epub_cover_falls_back_to_first_image_manifest_item():
    epub = _epub(
        manifest=(
            '<item id="chapter" href="chapter.xhtml" '
            'media-type="application/xhtml+xml"/>'
            '<item id="image" href="image.png" media-type="image/png"/>'
        ),
        files={"OPS/image.png": b"fallback cover"},
    )

    assert extract_epub_cover(epub) == b"fallback cover"


def test_extract_epub_cover_ignores_manifest_fragment():
    epub = _epub(
        manifest='<item id="cover" href="cover.jpg#front" media-type="image/jpeg"/>',
        files={"OPS/cover.jpg": b"fragment cover"},
    )

    assert extract_epub_cover(epub) == b"fragment cover"


def test_extract_epub_cover_returns_none_without_an_image():
    epub = _epub(
        manifest=(
            '<item id="chapter" href="chapter.xhtml" '
            'media-type="application/xhtml+xml"/>'
        ),
        files={"OPS/chapter.xhtml": b"chapter"},
    )

    assert extract_epub_cover(epub) is None


def test_extract_epub_cover_returns_none_for_missing_cover_file():
    epub = _epub(
        manifest='<item id="cover" href="missing.jpg" media-type="image/jpeg"/>',
        files={},
    )

    assert extract_epub_cover(epub) is None


def test_extract_cover_dispatches_to_format_helper():
    assert extract_cover(b"not a supported format", "txt") is None
