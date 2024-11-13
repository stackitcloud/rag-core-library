"""Dataclass holding the information found in a document."""

import dataclasses

from extractor_api_lib.document_parser.content_type import ContentType


@dataclasses.dataclass
class InformationPiece:
    """Dataclass holding the information found in a document."""

    type: ContentType  # noqa: A003  # type of the information
    metadata: dict  # should contain at least "document" and "page"
    page_content: str | None = None  # page content
