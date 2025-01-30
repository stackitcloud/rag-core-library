import json

import pytest
from langchain_core.documents import Document

from rag_core_api.mapper.information_piece_mapper import InformationPieceMapper
from rag_core_api.models.key_value_pair import KeyValuePair
from rag_core_api.models.information_piece import InformationPiece


DOCUMENT_URL_KEY = "document_url"
IMAGE_CONTENT_KEY = "base64_image"


@pytest.fixture
def minimal_text_documents() -> tuple[InformationPiece, Document]:
    metadata = {
        "document": "https://docs.stackit.cloud/",
        "document_url": "https://docs.stackit.cloud/display/STACKIT/Object+Storage+S3+compatible",
        "type": "TEXT",
    }
    page_content = """STACKIT Object Storage is a flexible scalable cloud storage architecture that stores and manages
    data as objects.

    An object typically consists of the data itself, metadata and a unique identifier. The object metadata can be
    custom defined and the identifier of the object is unique within a given namespace. This architecture makes it
    possible to store all files in a flat structure without hierarchy as data can be addressed through it´s unique
    identifier. That stands in contrast to other storage architectures like file based storage where data is organized
    in a hierarchical structure of folders and files and the metadata is fixed to a few values. This architecture makes
    the Object Storage extremely scalable and perfect to store big amount of unstructured data on it. Data on Object
    Storage can be accessed through HTTPS-based RESTful APIs known as RESTful Web service.

    ## Use cases"""  # noqa E501

    langchain_doc = Document(page_content=page_content, metadata=metadata)

    source_doc = InformationPiece(
        page_content=page_content,
        metadata=[KeyValuePair(key=key, value=value) for key, value in metadata.items()],
        type=metadata["type"],
    )

    return source_doc, langchain_doc


@pytest.fixture
def minimal_image_documents() -> tuple[InformationPiece, Document]:
    metadata = {
        "document": "https://docs.stackit.cloud/",
        "document_url": "https://docs.stackit.cloud/display/STACKIT/Object+Storage+S3+compatible",
        "type": "IMAGE",
        "base64_image": "SGVsbG8gV29ybGQh",
    }
    page_content = ""

    langchain_doc = Document(page_content=page_content, metadata=metadata)
    source_doc_metadata = [KeyValuePair(key=key, value=value) for key, value in metadata.items()]
    source_doc = InformationPiece(
        page_content=page_content,
        metadata=source_doc_metadata,
        type=metadata["type"],
    )

    return source_doc, langchain_doc


@pytest.fixture
def missing_document_url_documents(minimal_text_documents) -> tuple[InformationPiece, Document]:
    source_doc, langchain_doc = minimal_text_documents
    source_doc.metadata = [x for x in source_doc.metadata if x.key != DOCUMENT_URL_KEY]

    del langchain_doc.metadata[DOCUMENT_URL_KEY]
    return source_doc, langchain_doc


@pytest.fixture
def missing_image_content_documents(minimal_image_documents) -> tuple[InformationPiece, Document]:
    source_doc, langchain_doc = minimal_image_documents
    source_doc.metadata = [x for x in source_doc.metadata if x.key != IMAGE_CONTENT_KEY]

    del langchain_doc.metadata[IMAGE_CONTENT_KEY]
    return source_doc, langchain_doc


def test_mapping(minimal_text_documents):
    original_source_doc, original_langchain_doc = minimal_text_documents

    mapped_source_doc = InformationPieceMapper.langchain_document2information_piece(original_langchain_doc)
    mapped_langchain_doc = InformationPieceMapper.information_piece2langchain_document(original_source_doc)

    double_mapped_langchain_doc = InformationPieceMapper.information_piece2langchain_document(mapped_source_doc)
    double_mapped_source_doc = InformationPieceMapper.langchain_document2information_piece(mapped_langchain_doc)

    assert original_langchain_doc == mapped_langchain_doc
    assert original_source_doc == mapped_source_doc

    assert original_langchain_doc == double_mapped_langchain_doc
    assert original_source_doc == double_mapped_source_doc


def test_image_mapping(minimal_image_documents):
    original_source_doc, original_langchain_doc = minimal_image_documents

    mapped_source_doc = InformationPieceMapper.langchain_document2information_piece(original_langchain_doc)
    mapped_langchain_doc = InformationPieceMapper.information_piece2langchain_document(original_source_doc)

    double_mapped_langchain_doc = InformationPieceMapper.information_piece2langchain_document(mapped_source_doc)
    double_mapped_source_doc = InformationPieceMapper.langchain_document2information_piece(mapped_langchain_doc)

    assert original_langchain_doc == mapped_langchain_doc
    assert original_source_doc == mapped_source_doc

    assert original_langchain_doc == double_mapped_langchain_doc
    assert original_source_doc == double_mapped_source_doc


def test_mapping_fails_with_missing_document_url(missing_document_url_documents):
    original_source_doc, original_langchain_doc = missing_document_url_documents

    with pytest.raises(ValueError, match=DOCUMENT_URL_KEY):
        InformationPieceMapper.information_piece2langchain_document(original_source_doc)

    with pytest.raises(ValueError, match=DOCUMENT_URL_KEY):
        InformationPieceMapper.langchain_document2information_piece(original_langchain_doc)


def test_mapping_fails_with_missing_image_content(missing_image_content_documents):
    original_source_doc, original_langchain_doc = missing_image_content_documents

    with pytest.raises(ValueError, match=IMAGE_CONTENT_KEY):
        InformationPieceMapper.information_piece2langchain_document(original_source_doc)

    with pytest.raises(ValueError, match=IMAGE_CONTENT_KEY):
        InformationPieceMapper.langchain_document2information_piece(original_langchain_doc)
