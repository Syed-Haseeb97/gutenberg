"""Generic cover extraction helpers for document formats."""

import io
import zipfile
from pathlib import PurePosixPath
from urllib.parse import unquote, urldefrag

import pymupdf
from lxml import etree  # pyright: ignore[reportAttributeAccessIssue]


def extract_cover(content: bytes, format_name: str) -> bytes | None:
    """Extract raw cover image bytes from a supported document."""
    if format_name == "pdf":
        return extract_pdf_cover(content)
    if format_name == "epub":
        return extract_epub_cover(content)
    return None


def extract_pdf_cover(content: bytes) -> bytes | None:
    """Render the first page of a PDF as PNG bytes."""
    if not content:
        return None
    document = pymupdf.open(stream=content, filetype="pdf")
    try:
        if document.page_count == 0:
            return None
        pixmap = document[0].get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), alpha=False)
        return pixmap.tobytes("png")
    finally:
        document.close()


def extract_epub_cover(content: bytes) -> bytes | None:
    """Extract the declared or first image cover from an EPUB archive."""
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        parser = etree.XMLParser(resolve_entities=False, no_network=True)
        container = etree.fromstring(archive.read("META-INF/container.xml"), parser)
        rootfile = container.find(".//{*}rootfile")
        if rootfile is None or not (opf_path := rootfile.get("full-path")):
            return None

        package = etree.fromstring(archive.read(opf_path), parser)
        manifest = {
            item.get("id"): item
            for item in package.findall(".//{*}manifest/{*}item")
            if item.get("id") and item.get("href")
        }
        cover_id = next(
            (
                meta.get("content")
                for meta in package.findall(".//{*}metadata/{*}meta")
                if meta.get("name") == "cover" and meta.get("content")
            ),
            None,
        )
        cover_item = manifest.get(cover_id) if cover_id else None
        if cover_item is None:
            cover_item = next(
                (
                    item
                    for item in manifest.values()
                    if "cover-image" in item.get("properties", "").split()
                ),
                None,
            )
        if cover_item is None:
            cover_item = next(
                (
                    item
                    for item in manifest.values()
                    if item.get("media-type", "").startswith("image/")
                ),
                None,
            )
        if cover_item is None:
            return None

        href = unquote(urldefrag(cover_item.attrib["href"])[0])
        cover_path = PurePosixPath(opf_path).parent / href
        if str(cover_path) not in archive.namelist():
            return None
        return archive.read(str(cover_path))
