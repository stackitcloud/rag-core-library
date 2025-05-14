from http.client import HTTPException
import logging
import os
from pathlib import Path
from typing import Optional, Tuple, Union
from threading import Thread
import urllib
import tempfile

from pydantic import StrictBytes, StrictStr
from fastapi import UploadFile, status
from langchain_core.documents import Document
from asyncio import run

from admin_api_lib.models.key_value_pair import KeyValuePair
from admin_api_lib.rag_backend_client.openapi_client.api.rag_api import RagApi
from admin_api_lib.impl.mapper.informationpiece2document import InformationPiece2Document
from admin_api_lib.api_endpoints.document_deleter import DocumentDeleter
from admin_api_lib.api_endpoints.source_uploader import SourceUploader
from admin_api_lib.chunker.chunker import Chunker
from admin_api_lib.models.status import Status
from admin_api_lib.extractor_api_client.extractor_api_client import ExtractorApiClient
from admin_api_lib.impl.key_db.file_status_key_value_store import FileStatusKeyValueStore
from admin_api_lib.information_enhancer.information_enhancer import InformationEnhancer
from admin_api_lib.utils.utils import sanitize_document_name

logger = logging.getLogger(__name__)


class DefaultSourceUploader(SourceUploader):

    def __init__(
        self,
        extractor_api: ExtractorApiClient,
        key_value_store: FileStatusKeyValueStore,
        information_enhancer: InformationEnhancer,
        chunker: Chunker,
        document_deleter: DocumentDeleter,
        rag_api: RagApi,
        information_mapper: InformationPiece2Document,
    ):
        self._extractor_api = extractor_api
        self._rag_api = rag_api
        self._key_value_store = key_value_store
        self._information_mapper = information_mapper
        self._information_enhancer = information_enhancer
        self._chunker = chunker
        self._document_deleter = document_deleter
        self._background_threads = []

    async def upload_source(
        self,
        base_url: str,
        type: StrictStr,
        name: StrictStr,
        file: Optional[UploadFile],
        kwargs: Optional[list[KeyValuePair]],
    ) -> None:
        self._background_threads = [t for t in self._background_threads if t.is_alive()]
        source_name = f"{type}:{sanitize_document_name(name)}"
        try:
            # TODO: check if document already in processing state
            self._key_value_store.upsert(
                source_name, Status.PROCESSING
            )  # TODO: change to pipeline with timeout to error status
            filename = None
            if file:
                content = await file.read()
                filename = Path("/tmp/" + file.filename)
                with open(filename, "wb") as tmpfile:
                    tmpfile.write(content)
            thread = Thread(
                target=lambda: run(self._handle_source_upload(source_name, base_url, type, name, filename, kwargs))
            )
            thread.start()
            self._background_threads.append(thread)
        except ValueError as e:
            self._key_value_store.upsert(source_name, Status.ERROR)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            self._key_value_store.upsert(source_name, Status.ERROR)
            logger.error("Error while uploading %s = %s", source_name, str(e))
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    async def _handle_source_upload(
        self,
        source_name: str,
        base_url: str,
        type: StrictStr,
        name: StrictStr,
        file,  #: Optional[Union[StrictBytes, StrictStr, Tuple[StrictStr, StrictBytes]]],
        kwargs: Optional[list[KeyValuePair]],
    ):
        try:
            if file:                
                information_pieces = self._extractor_api.extract(type, source_name, str(file), kwargs)
            else:
                information_pieces = self._extractor_api.extract(type, source_name, None, kwargs)

            if not information_pieces:
                self._key_value_store.upsert(source_name, Status.ERROR)
                logger.error("No information pieces found in the document: %s", source_name)
            documents = [self._information_mapper.extractor_information_piece2document(x) for x in information_pieces]

            chunked_documents = self._chunker.chunk(documents)
            self._add_file_url(type, file, base_url, chunked_documents)

            enhanced_documents = await self._information_enhancer.ainvoke(chunked_documents)
            rag_information_pieces = [
                self._information_mapper.document2rag_information_piece(doc) for doc in enhanced_documents
            ]

            # Replace old document
            try:
                await self._document_deleter.adelete_document(source_name)
            except Exception as e:
                # deletion is allowed to fail
                pass
            self._rag_api.upload_information_piece(rag_information_pieces)
            self._key_value_store.upsert(source_name, Status.READY)
            logger.info("File uploaded successfully: %s", source_name)
            if file:
                os.remove(file)
        except Exception as e:
            self._key_value_store.upsert(source_name, Status.ERROR)
            logger.error("Error while uploading %s = %s", source_name, str(e))

    def _add_file_url(
        self, type: StrictStr, file: Optional[UploadFile], base_url: str, chunked_documents: list[Document]
    ):
        if type != "file":
            return

        document_url = f"{base_url.rstrip('/')}/document_reference/{urllib.parse.quote_plus(file.name)}"
        for idx, chunk in enumerate(chunked_documents):
            if chunk.metadata["id"] in chunk.metadata["related"]:
                chunk.metadata["related"].remove(chunk.metadata["id"])
            chunk.metadata.update(
                {
                    "chunk": idx,
                    "chunk_length": len(chunk.page_content),
                    "document_url": document_url,
                }
            )
