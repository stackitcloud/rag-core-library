"""Module for the DefaultCollectionDuplicator class."""
from rag_core_api.api_endpoints.collection_duplicator import CollectionDuplicator
from rag_core_api.impl.settings.vector_db_settings import VectorDatabaseSettings
from rag_core_api.vector_databases.vector_database import VectorDatabase


class DefaultCollectionDuplicator(CollectionDuplicator):
    def __init__(self, settings: VectorDatabaseSettings, vector_database: VectorDatabase):
        self._settings = settings
        self._vector_database = vector_database

    async def aduplicate_collection(self) -> None:
        self._vector_database.duplicate_alias_tagged_collection()
