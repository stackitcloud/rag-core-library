"""Module for the DefaultCollectionDuplicator class."""

from rag_core_api.api_endpoints.collection_duplicator import CollectionDuplicator

#TODO: add doc strings, revise accordingly

class DefaultCollectionDuplicator(CollectionDuplicator):


    async def aduplicate_collection(self) -> None:
        raise NotImplementedError
