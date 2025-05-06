"""Default collection switcher module.

This module provides the DefaultCollectionSwitcher class, which switches
 the vector database to the most recently created collection.

"""

from rag_core_api.api_endpoints.collection_switcher import CollectionSwitcher


class DefaultCollectionSwitcher(CollectionSwitcher):
    """Default implementation of CollectionSwitcher."""

    def __init__(self, vector_database):
        """Initialize the DefaultCollectionSwitcher.

        Parameters
        ----------
        vector_database : VectorDatabase
            The vector database instance to interact with.
        """
        super().__init__(vector_database)

    async def aswitch_collection(self) -> None:
        """Asynchronously switch to the latest collection.

        Retrieves the name of the most recently created collection from the
        vector database and performs the switch.

        Returns
        -------
        None
        """
        collection_name = self._vector_database.get_sorted_collection_names()[-1]
        self._vector_database.switch_collections(collection_name)
