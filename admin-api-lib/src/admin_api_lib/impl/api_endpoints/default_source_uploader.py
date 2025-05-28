
from concurrent.futures import ThreadPoolExecutor
import logging
import asyncio
from threading import Thread, Event
from contextlib import suppress

from pydantic import StrictStr
from fastapi import status, HTTPException
from langchain_core.documents import Document

from admin_api_lib.extractor_api_client.openapi_client.api.extractor_api import ExtractorApi
from admin_api_lib.extractor_api_client.openapi_client.models.extraction_parameters import ExtractionParameters
from admin_api_lib.models.key_value_pair import KeyValuePair
from admin_api_lib.rag_backend_client.openapi_client.api.rag_api import RagApi
from admin_api_lib.impl.mapper.informationpiece2document import InformationPiece2Document
from admin_api_lib.api_endpoints.document_deleter import DocumentDeleter
from admin_api_lib.api_endpoints.source_uploader import SourceUploader
from admin_api_lib.chunker.chunker import Chunker
from admin_api_lib.models.status import Status
from admin_api_lib.impl.key_db.file_status_key_value_store import FileStatusKeyValueStore
from admin_api_lib.information_enhancer.information_enhancer import InformationEnhancer
from admin_api_lib.utils.utils import sanitize_document_name
from admin_api_lib.rag_backend_client.openapi_client.models.information_piece import (
    InformationPiece as RagInformationPiece,
)

logger = logging.getLogger(__name__)

class UploadCancelled(Exception):
    pass

class DefaultSourceUploader(SourceUploader):

    def __init__(
        self,
        extractor_api: ExtractorApi,
        key_value_store: FileStatusKeyValueStore,
        information_enhancer: InformationEnhancer,
        chunker: Chunker,
        document_deleter: DocumentDeleter,
        rag_api: RagApi,
        information_mapper: InformationPiece2Document,
    ):
        """
        Initialize the DefaultSourceUploader.

        Parameters
        ----------
        extractor_api : ExtractorApi
            Client for the Extraction service.
        key_value_store : FileStatusKeyValueStore
            The key-value store for storing filename and the corresponding status.
        information_enhancer : InformationEnhancer
            The service for enhancing information.
        chunker : Chunker
            The service for chunking documents into chunks.
        document_deleter : DocumentDeleter
            The service for deleting documents.
        rag_api : RagApi
            The API for RAG backend.
        information_mapper : InformationPiece2Document
            The mapper for converting information pieces to langchain documents.
        """
        self._extractor_api = extractor_api
        self._rag_api = rag_api
        self._key_value_store = key_value_store
        self._information_mapper = information_mapper
        self._information_enhancer = information_enhancer
        self._chunker = chunker
        self._document_deleter = document_deleter
        self._background_tasks = []

    async def upload_source(
        self,
        base_url: str,
        source_type: StrictStr,
        name: StrictStr,
        kwargs: list[KeyValuePair],
        timeout: float = 300.0,
    ) -> None:
        # 1) prune finished tasks
        self._background_tasks = [
            (fut, ev) for fut, ev in self._background_tasks
            if not fut.done()
        ]

        source_name = f"{source_type}:{sanitize_document_name(name)}"
        try:
            self._check_if_already_in_processing(source_name)
            self._key_value_store.upsert(source_name, Status.PROCESSING)

            # 1) make a stop‐event for cooperative cancellation
            stop_event = Event()

            # 2) submit the real work to a ThreadPoolExecutor
            loop = asyncio.get_running_loop()
            # you can reuse one executor or make a new one
            executor = ThreadPoolExecutor(max_workers=1)
            future = loop.run_in_executor(
                executor,
                lambda: asyncio.run(
                    self._handle_source_upload(
                        source_name, source_type, kwargs, stop_event
                    )
                )
            )
            # track both thread‐future and its stop‐event
            self._background_tasks.append((future, stop_event))

            # 3) await with a timeout, *without* blocking the loop
            try:
                await asyncio.wait_for(future, timeout)
            except asyncio.TimeoutError:
                # mark error, signal the thread, and move on
                self._key_value_store.upsert(source_name, Status.ERROR)
                stop_event.set()
                logger.error("Upload of %s timed out; signaled stop_event", source_name)

        except ValueError as e:
            self._key_value_store.upsert(source_name, Status.ERROR)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            )
        except Exception as e:
            self._key_value_store.upsert(source_name, Status.ERROR)
            logger.error("Error while uploading %s = %s", source_name, str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )


    def _on_upload_timeout(self, source_name: str, thread: Thread) -> None:
        """
        Called by the event loop after `timeout` seconds.
        Sets the stop_event so that the worker can exit cleanly.
        """
        if thread.is_alive():
            logger.error("Upload of %s timed out; signaling thread to stop", source_name)
            # mark as error in your store
            self._key_value_store.upsert(source_name, Status.ERROR)
            # signal the worker to bail out at next checkpoint
            thread.stop_event.set()


    def _check_if_already_in_processing(self, source_name: str) -> None:
        """
        Checks if the source is already in processing state.

        Parameters
        ----------
        source_name : str
            The name of the source.

        Returns
        -------
        None

        Raises
        ------
        ValueError
            If the source is already in processing state.
        """
        existing = [s for name, s in self._key_value_store.get_all() if name == source_name]
        if any(s == Status.PROCESSING for s in existing):
            raise ValueError(f"Document {source_name} is already in processing state")

    @staticmethod
    def _ensure_not_cancelled(stop_event, source_name, store):
        if stop_event.is_set():
            # mark as error or cancelled if you like
            store.upsert(source_name, Status.ERROR)
            raise UploadCancelled()

    async def _handle_source_upload(
        self,
        source_name: str,
        source_type: StrictStr,
        kwargs: list[KeyValuePair],
        stop_event: Event
    ):
        try:
            information_pieces = self._extractor_api.extract_from_source(
                ExtractionParameters(
                    source_type=source_type,
                    document_name=source_name,
                    kwargs=[x.to_dict() for x in kwargs]
                )
            )

            if not information_pieces:
                self._key_value_store.upsert(source_name, Status.ERROR)
                logger.error("No information pieces found in the document: %s", source_name)
                return
            DefaultSourceUploader._ensure_not_cancelled(stop_event, source_name, self._key_value_store)
            documents: list[Document] = []
            for piece in information_pieces:
                documents.append(self._information_mapper.extractor_information_piece2document(piece))

            DefaultSourceUploader._ensure_not_cancelled(stop_event, source_name, self._key_value_store)
            chunked_documents = self._chunker.chunk(documents)

            DefaultSourceUploader._ensure_not_cancelled(stop_event, source_name, self._key_value_store)
            enhanced_documents = await self._information_enhancer.ainvoke(chunked_documents)

            DefaultSourceUploader._ensure_not_cancelled(stop_event, source_name, self._key_value_store)
            rag_information_pieces: list[RagInformationPiece] = []
            for doc in enhanced_documents:
                rag_information_pieces.append(
                    self._information_mapper.document2rag_information_piece(doc)
                )

            DefaultSourceUploader._ensure_not_cancelled(stop_event, source_name, self._key_value_store)
            with suppress(Exception):
                await self._document_deleter.adelete_document(source_name)

            self._rag_api.upload_information_piece(rag_information_pieces)

            self._key_value_store.upsert(source_name, Status.READY)
            logger.info("Source uploaded successfully: %s", source_name)

        except UploadCancelled:
            logger.info("Upload of %s aborted by timeout", source_name)
            return
        except Exception as e:
            # If it wasn’t our own cancellation, record the error
            if stop_event.is_set():
                logger.info("Upload of %s aborted due to timeout", source_name)
            else:
                self._key_value_store.upsert(source_name, Status.ERROR)
                logger.error("Error while uploading %s = %s", source_name, str(e))
