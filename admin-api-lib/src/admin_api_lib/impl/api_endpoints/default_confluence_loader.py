import json
import logging

from admin_api_lib.api_endpoints.confluence_loader import ConfluenceLoader
from admin_api_lib.api_endpoints.document_deleter import DocumentDeleter
from admin_api_lib.extractor_api_client.openapi_client.api.extractor_api import ExtractorApi
from admin_api_lib.impl.chunker.chunker import Chunker
from admin_api_lib.impl.mapper.confluence_settings_mapper import ConfluenceSettingsMapper
from admin_api_lib.information_enhancer.information_enhancer import InformationEnhancer
from admin_api_lib.rag_backend_client.openapi_client.api.rag_api import RagApi
from admin_api_lib.impl.key_db.file_status_key_value_store import FileStatusKeyValueStore
from admin_api_lib.impl.settings.confluence_settings import ConfluenceSettings
from admin_api_lib.impl.mapper.informationpiece2document import InformationPiece2Document
from admin_api_lib.models.status import Status
from admin_api_lib.rag_backend_client.openapi_client.models.content_type import ContentType
from admin_api_lib.rag_backend_client.openapi_client.models.information_piece import InformationPiece
from admin_api_lib.rag_backend_client.openapi_client.models.key_value_pair import KeyValuePair

from fastapi import HTTPException

logger = logging.getLogger(__name__)


class DefaultConfluenceLoader(ConfluenceLoader):
    DOCUMENT_METADATA_TYPE_KEY = "type"
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
        self._extractor_api = extractor_api
        self._rag_api = rag_api
        self._settings = settings
        self._key_value_store = key_value_store
        self._information_mapper = information_mapper
        self._information_enhancer = information_enhancer
        self._chunker = chunker
        self._document_deleter = document_deleter
        self._settings_mapper = settings_mapper

    async def aload_from_confluence(self) -> None:
        """
        Asynchronously loads content from Confluence using the configured settings.
        """
        if not (
            self._settings.url
            and self._settings.url.strip()
            and self._settings.space_key
            and self._settings.space_key.strip()
            and self._settings.token
            and self._settings.token.strip()
        ):
            raise HTTPException(501, "The confluence loader is not configured!")
        params = self._settings_mapper.map_settings_to_params(self._settings)
        try:
            self._key_value_store.upsert(self._settings.url, Status.UPLOADING)
            information_pieces = self._extractor_api.extract_from_confluence_post(params)
            documents = [self._information_mapper.information_piece2document(x) for x in information_pieces]
            chunked_documents = self._chunker.chunk(documents)
            rag_api_documents = []
            for document in chunked_documents:
                metadata = [
                    KeyValuePair(key=str(key), value=json.dumps(value)) for key, value in document.metadata.items()
                ]
                content_type = ContentType(document.metadata[self.DOCUMENT_METADATA_TYPE_KEY].upper())
                rag_api_documents.append(
                    InformationPiece(
                        type=content_type,
                        metadata=metadata,
                        page_content=document.page_content,
                    )
                )
        except Exception as e:
            self._key_value_store.upsert(self._settings.url, Status.ERROR)
            logger.error("Error while loading from Confluence: %s", str(e))
            raise HTTPException(500, f"Error loading from Confluence: {str(e)}") from e

        await self._delete_previous_information_pieces()
        self._upload_information_pieces(rag_api_documents)

    async def _delete_previous_information_pieces(self):
        try:
            await self._document_deleter.adelete_document(self._settings.url)
        except HTTPException as e:
            logger.error(
                (
                    "Error while trying to delete documents with id: %s before uploading %s."
                    "NOTE: Still continuing with upload."
                ),
                self._settings.url,
                e,
            )

    def _upload_information_pieces(self, rag_api_documents):
        try:
            self._rag_api.upload_information_piece(rag_api_documents)
            self._key_value_store.upsert(self._settings.url, Status.READY)
            logger.info("Confluence loaded successfully")
        except Exception as e:
            self._key_value_store.upsert(self._settings.url, Status.ERROR)
            logger.error("Error while uploading Confluence to the database: %s", str(e))
            raise HTTPException(500, f"Error loading from Confluence: {str(e)}") from e
