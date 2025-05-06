"""DefaultCollectionDuplicator module.

This module provides the DefaultCollectionDuplicator class for duplicating
alias-tagged collections in a vector database.
"""

from rag_core_api.api_endpoints.collection_duplicator import CollectionDuplicator
from rag_core_api.vector_databases.vector_database import VectorDatabase


class DefaultCollectionDuplicator(CollectionDuplicator):
    """Duplicate an alias-tagged collection.

    Parameters
    ----------
    vector_database : VectorDatabase
        An instance of VectorDatabase to perform duplication operations.
    """

    def __init__(self, vector_database: VectorDatabase):
        """Initialize the DefaultCollectionDuplicator.

        Parameters
        ----------
        vector_database : VectorDatabase
            The vector database used for duplication operations.
        """
        super().__init__(vector_database)

    async def aduplicate_collection(self) -> None:
        """Duplicate the alias-tagged collection in the vector database.

        This asynchronous method triggers the duplication process for collections
        identified by alias tags in the vector database.

        Returns
        -------
        None
        """
        self._vector_database.duplicate_alias_tagged_collection()
