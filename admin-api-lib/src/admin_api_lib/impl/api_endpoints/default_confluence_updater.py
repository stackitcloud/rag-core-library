"""Module for the DefaultConfluenceLoader class."""

import logging
from asyncio import run
from threading import Thread
import threading

from fastapi import HTTPException, status
from langchain_core.documents import Document

from admin_api_lib.api_endpoints.confluence_updater import ConfluenceUpdater
from admin_api_lib.api_endpoints.document_deleter import DocumentDeleter
from admin_api_lib.chunker.chunker import Chunker
from admin_api_lib.confluence_handler.confluence_handler import ConfluenceHandler
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


class DefaultConfluenceUpdater(ConfluenceUpdater, ConfluenceHandler):
    """DefaultConfluenceUpdater is responsible for loading content from Confluence asynchronously."""

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
        super().__init__(
            extractor_api=extractor_api,
            settings=settings,
            information_mapper=information_mapper,
            rag_api=rag_api,
            key_value_store=key_value_store,
            information_enhancer=information_enhancer,
            chunker=chunker,
            document_deleter=document_deleter,
            settings_mapper=settings_mapper
        )
        self._background_thread: threading.Thread = None

    async def aupdate_from_confluence(self) -> None:
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
        self._background_thread = Thread(target=lambda: run(self._aload_from_confluence(use_latest_collection=True)))
        self._background_thread.start()

    async def _aload_from_confluence(self,use_latest_collection:bool|None=None) -> None:

        threads = []
        results: dict[int, list[Document]] = {}

        def worker(idx: int):
            pieces = run(self._process_confluence(idx))
            results[idx] = pieces

        for idx in range(len(self._settings.url)):
            t = threading.Thread(target=worker, args=(idx,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self._rag_api.duplicate_collection()
        await self._update_vector_db(results, use_latest_collection=use_latest_collection)
        self._rag_api.switch_collection()

