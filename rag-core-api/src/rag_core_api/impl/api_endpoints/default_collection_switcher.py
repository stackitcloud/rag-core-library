"""Module for the DefaultCollectionDuplicator class."""

from rag_core_api.api_endpoints.collection_switcher import CollectionSwitcher

# TODO: add doc strings, revise accordingly


class DefaultCollectionSwitcher(CollectionSwitcher):
    async def aswitch_collection(self) -> None:
        raise NotImplementedError
