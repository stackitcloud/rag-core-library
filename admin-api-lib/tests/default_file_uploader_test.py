import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from fastapi import UploadFile
import threading, time

from admin_api_lib.impl.api_endpoints.default_file_uploader import DefaultFileUploader
from admin_api_lib.models.status import Status
from admin_api_lib.utils.utils import sanitize_document_name
from admin_api_lib.impl.api_endpoints import default_file_uploader

@ pytest.fixture
def mocks():
    extractor_api = MagicMock()
    key_value_store = MagicMock()
    key_value_store.get_all.return_value = []
    information_enhancer = MagicMock()
    information_enhancer.ainvoke = AsyncMock()
    chunker = MagicMock()
    document_deleter = MagicMock()
    document_deleter.adelete_document = AsyncMock()
    rag_api = MagicMock()
    information_mapper = MagicMock()
    return extractor_api, key_value_store, information_enhancer, chunker, document_deleter, rag_api, information_mapper

@ pytest.mark.asyncio
async def test_handle_file_upload_success(mocks):
    extractor_api, key_value_store, information_enhancer, chunker, document_deleter, rag_api, information_mapper = mocks
    # setup mocks
    dummy_piece = MagicMock()
    extractor_api.extract_from_file_post.return_value = [dummy_piece]
    dummy_doc = MagicMock()
    information_mapper.extractor_information_piece2document.return_value = dummy_doc
    chunker.chunk.return_value = [dummy_doc]
    information_enhancer.ainvoke.return_value = [dummy_doc]
    dummy_rag = {"foo": "bar"}
    information_mapper.document2rag_information_piece.return_value = dummy_rag

    uploader = DefaultFileUploader(
        extractor_api, key_value_store, information_enhancer, chunker,
        document_deleter, rag_api, information_mapper, file_service=MagicMock()
    )

    await uploader._handle_source_upload("s3path", "file:doc1", "doc1.txt", "http://base")

    key_value_store.upsert.assert_any_call("file:doc1", Status.READY)
    rag_api.upload_information_piece.assert_called_once_with([dummy_rag])
    document_deleter.adelete_document.assert_awaited_once_with("file:doc1")

@ pytest.mark.asyncio
async def test_handle_file_upload_no_info_pieces(mocks):
    extractor_api, key_value_store, information_enhancer, chunker, document_deleter, rag_api, information_mapper = mocks
    extractor_api.extract_from_file_post.return_value = []

    uploader = DefaultFileUploader(
        extractor_api, key_value_store, information_enhancer, chunker,
        document_deleter, rag_api, information_mapper, file_service=MagicMock()
    )
    filename = "file:doc2"
    await uploader._handle_source_upload("s3path", filename, "doc2.txt", "http://base")

    key_value_store.upsert.assert_any_call(filename, Status.ERROR)
    information_mapper.extractor_information_piece2document.assert_not_called()
    rag_api.upload_information_piece.assert_not_called()

@ pytest.mark.asyncio
async def test_upload_file_already_processing_raises_error(mocks):
    extractor_api, key_value_store, information_enhancer, chunker, document_deleter, rag_api, information_mapper = mocks
    base_url = "http://base"
    file = MagicMock(spec=UploadFile)
    file.filename = "doc3.txt"
    file.read = AsyncMock(return_value=b"")
    source_name = f"file:{sanitize_document_name(file.filename)}"
    key_value_store.get_all.return_value = [(source_name, Status.PROCESSING)]

    uploader = DefaultFileUploader(
        extractor_api, key_value_store, information_enhancer, chunker,
        document_deleter, rag_api, information_mapper, file_service=MagicMock()
    )

    with pytest.raises(HTTPException):
        await uploader.upload_file(base_url, file)
    key_value_store.upsert.assert_any_call(source_name, Status.ERROR)

@ pytest.mark.asyncio
async def test_upload_file_starts_thread(mocks, monkeypatch):
    extractor_api, key_value_store, information_enhancer, chunker, document_deleter, rag_api, information_mapper = mocks
    base_url = "http://base"
    file = MagicMock(spec=UploadFile)
    file.filename = "doc4.txt"
    file.read = AsyncMock(return_value=b"content")
    key_value_store.get_all.return_value = []
    source_name = f"file:{sanitize_document_name(file.filename)}"

    dummy_thread = MagicMock()
    monkeypatch.setattr(default_file_uploader, 'Thread', lambda *args, **kwargs: dummy_thread)

    uploader = DefaultFileUploader(
        extractor_api, key_value_store, information_enhancer, chunker,
        document_deleter, rag_api, information_mapper, file_service=MagicMock()
    )

    await uploader.upload_file(base_url, file)

    key_value_store.upsert.assert_any_call(source_name, Status.PROCESSING)
    dummy_thread.start.assert_called_once()

@ pytest.mark.asyncio
async def test_upload_file_timeout_error(mocks, monkeypatch):
    extractor_api, key_value_store, information_enhancer, chunker, document_deleter, rag_api, information_mapper = mocks
    base_url = "http://base"
    file = MagicMock(spec=UploadFile)
    file.filename = "slow.txt"
    file.read = AsyncMock(return_value=b"")
    key_value_store.get_all.return_value = []
    source_name = f"file:{sanitize_document_name(file.filename)}"

    # fast fake handler that sleeps long
    async def fake_handle(self, s3_path, source_name_arg, filename, base_url_arg):
        await asyncio.sleep(3600)
    monkeypatch.setattr(
        default_file_uploader.DefaultFileUploader,
        '_handle_source_upload',
        fake_handle
    )
    def FakeThread(target, args=(), **kwargs):
        class T:
            def start(self_inner): target(*args)
            def is_alive(self_inner): return False
        return T()
    monkeypatch.setattr(default_file_uploader, 'Thread', FakeThread)

    uploader = DefaultFileUploader(
        extractor_api, key_value_store, information_enhancer, chunker,
        document_deleter, rag_api, information_mapper, file_service=MagicMock()
    )

    await uploader.upload_file(base_url, file, timeout=0.1)
    calls = [c.args for c in key_value_store.upsert.call_args_list]
    assert (source_name, Status.PROCESSING) in calls
    assert (source_name, Status.ERROR) in calls
