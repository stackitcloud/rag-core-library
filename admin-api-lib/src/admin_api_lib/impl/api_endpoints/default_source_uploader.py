from http.client import HTTPException
import logging
from asyncio import run
from threading import Thread
from contextlib import suppress

from pydantic import StrictStr
from fastapi import status


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

logger = logging.getLogger(__name__)


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
        self._background_threads = []

    async def upload_source(
        self,
        base_url: str,
        source_type: StrictStr,
        name: StrictStr,
        kwargs: list[KeyValuePair],
    ) -> None:
        """
        Uploads the parameters for source content extraction.

        Parameters
        ----------
        base_url : str
            The base url of the service. Is used to determine the download link of the source.
        source_type : str
            The type of the source. Is used by the extractor service to determine the correct extraction method.
        name : str
            Display name of the source.
        kwargs : list[KeyValuePair]
            List of KeyValuePair with parameters used for the extraction.

        Returns
        -------
        None
        """
        self._background_threads = [t for t in self._background_threads if t.is_alive()]
        source_name = f"{source_type}:{sanitize_document_name(name)}"
        try:
            # TODO: check if document already in processing state
            self._key_value_store.upsert(
                source_name, Status.PROCESSING
            )  # TODO: change to pipeline with timeout to error status
            thread = Thread(
                target=lambda: run(self._handle_source_upload(source_name, source_type, kwargs))
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
        source_type: StrictStr,
        kwargs: list[KeyValuePair],
    ):
        try:
            information_pieces = self._extractor_api.extract_from_source(
                ExtractionParameters(source_type=source_type, document_name=source_name, kwargs=[x.to_dict() for x in kwargs])
            )

            if not information_pieces:
                self._key_value_store.upsert(source_name, Status.ERROR)
                logger.error("No information pieces found in the document: %s", source_name)
            documents = [self._information_mapper.extractor_information_piece2document(x) for x in information_pieces]

            chunked_documents = self._chunker.chunk(documents)

            enhanced_documents = await self._information_enhancer.ainvoke(chunked_documents)
            rag_information_pieces = [
                self._information_mapper.document2rag_information_piece(doc) for doc in enhanced_documents
            ]

            # Replace old document, deletion is allowed to fail
            with suppress(Exception):
                await self._document_deleter.adelete_document(source_name)

            self._rag_api.upload_information_piece(rag_information_pieces)
            self._key_value_store.upsert(source_name, Status.READY)
            logger.info("Source uploaded successfully: %s", source_name)
        except Exception as e:
            self._key_value_store.upsert(source_name, Status.ERROR)
            logger.error("Error while uploading %s = %s", source_name, str(e))
