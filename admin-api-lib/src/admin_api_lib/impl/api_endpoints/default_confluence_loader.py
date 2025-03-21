"""Module for the DefaultConfluenceLoader class."""

import logging
from asyncio import run
from threading import Thread
import threading

from fastapi import HTTPException, status
from langchain_core.documents import Document

from admin_api_lib.api_endpoints.confluence_loader import ConfluenceLoader
from admin_api_lib.api_endpoints.document_deleter import DocumentDeleter
from admin_api_lib.chunker.chunker import Chunker
from admin_api_lib.extractor_api_client.openapi_client.api.extractor_api import (
    ExtractorApi,
)
from admin_api_lib.impl.key_db.file_status_key_value_store import (
    FileStatusKeyValueStore,
)
from admin_api_lib.impl.mapper.confluence_settings_mapper import (
    ConfluenceSettingsMapper,
)
from admin_api_lib.impl.mapper.informationpiece2document import (
    InformationPiece2Document,
)
from admin_api_lib.impl.settings.confluence_settings import ConfluenceSettings
from admin_api_lib.information_enhancer.information_enhancer import InformationEnhancer
from admin_api_lib.models.status import Status
from admin_api_lib.rag_backend_client.openapi_client.api.rag_api import RagApi
from admin_api_lib.utils.utils import sanitize_document_name

logger = logging.getLogger(__name__)


class DefaultConfluenceLoader(ConfluenceLoader):
    """
    DefaultConfluenceLoader is responsible for loading content from Confluence asynchronously.

    Attributes
    ----------
    CONFLUENCE_SPACE : str
        The Confluence space key.
    """

    CONFLUENCE_SPACE = "confluence_space"

    def __init__(
        self,
        extractor_api: ExtractorApi,
        settings: ConfluenceSettings,
        information_mapper: InformationPiece2Document,
        rag_api: RagApi,
        key_value_store: FileStatusKeyValueStore,
        information_enhancer: InformationEnhancer,
        chunker: Chunker,
        document_deleter: DocumentDeleter,
        settings_mapper: ConfluenceSettingsMapper,
    ):
        """
        Initialize the DefaultConfluenceLoader with the provided dependencies.

        Parameters
        ----------
        extractor_api : ExtractorApi
            The API for extracting information.
        settings : ConfluenceSettings
            The settings for Confluence.
        information_mapper : InformationPiece2Document
            The mapper for information pieces to langchain documents.
        rag_api : RagApi
            The API client for interacting with the RAG backend system.
        key_value_store : FileStatusKeyValueStore
            The key-value store to store file names and the corresponding file statuses.
        information_enhancer : InformationEnhancer
            The enhancer for information pieces.
        chunker : Chunker
            The chunker for breaking down documents into chunks.
        document_deleter : DocumentDeleter
            The deleter for documents from S3 Storage and Vector Database.
        settings_mapper : ConfluenceSettingsMapper
            The mapper to map the Confluence settings to confluence parameters.
        """
        self._extractor_api = extractor_api
        self._rag_api = rag_api
        self._settings = settings
        self._key_value_store = key_value_store
        self._information_mapper = information_mapper
        self._information_enhancer = information_enhancer
        self._chunker = chunker
        self._document_deleter = document_deleter
        self._settings_mapper = settings_mapper
        self._background_thread = None
        self._document_key = None

    async def aload_from_confluence(self) -> None:
        """
        Asynchronously loads content from Confluence using the configured settings.

        Raises
        ------
        HTTPException
            If the Confluence loader is not configured or if a load is already in progress.
        """
        for index in range(len(self._settings.url)):
            if not (
                self._settings.url[index].strip()
                and self._settings.space_key[index].strip()
                and self._settings.token[index].strip()
            ):
                raise HTTPException(
                    status.HTTP_501_NOT_IMPLEMENTED,
                    "The confluence loader is not configured! Required fields are missing.",
                )

        if self._background_thread is not None and self._background_thread.is_alive():
            raise HTTPException(
                status.HTTP_423_LOCKED, "Confluence loader is locked... Please wait for the current load to finish."
            )
        self._background_thread = Thread(target=lambda: run(self._aload_from_confluence()))
        self._background_thread.start()

    async def _aload_from_confluence(self) -> None:
        async def process_confluence(index):
            logger.info("Loading from Confluence %s", self._settings.url[index])
            self._sanitize_document_name(index=index)

            params = self._settings_mapper.map_settings_to_params(self._settings, index)
            try:
                self._key_value_store.upsert(self._settings.document_name[index], Status.PROCESSING)
                information_pieces = self._extractor_api.extract_from_confluence_post(params)
                documents = [
                    self._information_mapper.extractor_information_piece2document(x) for x in information_pieces
                ]
                documents = await self._aenhance_langchain_documents(documents)
                chunked_documents = self._chunker.chunk(documents)
                rag_information_pieces = [
                    self._information_mapper.document2rag_information_piece(doc) for doc in chunked_documents
                ]
            except Exception as e:
                self._key_value_store.upsert(self._settings.document_name[index], Status.ERROR)

                logger.error("Error while loading from Confluence: %s", str(e))
                raise HTTPException(
                    status.HTTP_500_INTERNAL_SERVER_ERROR, f"Error loading from Confluence: {str(e)}"
                ) from e

            await self._delete_previous_information_pieces(index=index)
            self._key_value_store.upsert(self._settings.document_name[index], Status.UPLOADING)
            self._upload_information_pieces(rag_information_pieces, index=index)

        threads = []
        for idx in range(len(self._settings.url)):
            t = threading.Thread(target=lambda idx=idx: run(process_confluence(idx)))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()

    async def _aenhance_langchain_documents(self, documents: list[Document]):
        try:
            return await self._information_enhancer.ainvoke(documents)
        except Exception as e:
            logger.error("Exception occured while enhancing confluence langchain document %s" % e)
            raise e

    async def _delete_previous_information_pieces(self, index=0):
        try:
            await self._document_deleter.adelete_document(self._settings.document_name[index])
        except HTTPException as e:
            logger.error(
                (
                    "Error while trying to delete documents with id: %s before uploading %s."
                    "NOTE: Still continuing with upload."
                ),
                self._settings.document_name[index],
                e,
            )

    def _upload_information_pieces(self, rag_api_documents, index=0):
        try:
            self._rag_api.upload_information_piece(rag_api_documents)
            self._key_value_store.upsert(self._settings.document_name[index], Status.READY)
            logger.info("Confluence loaded successfully")
        except Exception as e:
            self._key_value_store.upsert(self._settings.document_name[index], Status.ERROR)
            logger.error("Error while uploading Confluence to the database: %s", str(e))
            raise HTTPException(500, f"Error loading from Confluence: {str(e)}") from e

    def _sanitize_document_name(self, index) -> None:
        document_name = (
            self._settings.document_name[index] if self._settings.document_name[index] else self._settings.url[index]
        )
        document_name = document_name.replace("http://", "").replace("https://", "")

        self._settings.document_name[index] = sanitize_document_name(document_name)
