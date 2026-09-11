"""Cover extraction for Open Textbook Library downloads.

The OTL API does not provide cover-image URLs. Covers are therefore derived
from the downloaded source file: the first PDF page or the EPUB package's
declared cover image.
"""

from typing import Protocol
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from gutenberg2zim.constants import logger
from gutenberg2zim.core.covers import extract_cover as extract_raw_cover
from gutenberg2zim.core.rewriters.image_rewriter import ImageProcessor


class CoverFetchEngine(Protocol):
    """Minimal download interface required to fetch a page cover."""

    def fetch_bytes(self, url: str) -> bytes: ...


def extract_cover(content: bytes, format_name: str) -> bytes | None:
    """Extract and WebP-encode a cover image from a downloaded book file."""
    try:
        image = extract_raw_cover(content, format_name)
        return ImageProcessor.optimize_image_content(image) if image else None
    except Exception as exc:
        logger.debug("Could not extract %s cover: %s", format_name, exc)
        return None


def fetch_page_cover(engine: CoverFetchEngine, source_url: str | None) -> bytes | None:
    """Fetch the cover advertised by an OTL book page and encode it as WebP."""
    if not source_url:
        return None
    try:
        page_url = f"{source_url.rstrip('/')}.html"
        soup = BeautifulSoup(engine.fetch_bytes(page_url), "html.parser")
        # OTL's og:image is a landscape social-media card. The page cover is
        # the portrait book image shown to readers, so always prefer it.
        cover = soup.find("img", class_="cover")
        image_url = cover.get("src") if cover else None
        if not image_url:
            image = soup.find("meta", property="og:image")
            image_url = image.get("content") if image else None
        if not image_url:
            return None
        if not isinstance(image_url, str):
            return None
        return ImageProcessor.optimize_image_content(
            engine.fetch_bytes(urljoin(page_url, image_url))
        )
    except Exception as exc:
        logger.debug("Could not fetch OTL page cover for %s: %s", source_url, exc)
        return None
