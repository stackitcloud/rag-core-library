"""
collection_duplicator module.

Defines the abstract base class CollectionDuplicator for duplicating
collections in a vector database.
"""

from abc import ABC, abstractmethod
from rag_core_api.vector_databases.vector_database import VectorDatabase


class CollectionDuplicator(ABC):
    """
    Abstract base class for duplicating a collection in a vector database.

    Parameters
    ----------
    vector_database : VectorDatabase
        The vector database instance to use for performing the duplication.
    """

    def __init__(self, vector_database: VectorDatabase):
        """
        Initialize the CollectionDuplicator with a vector database.

        Parameters
        ----------
        vector_database : VectorDatabase
            The vector database instance to use for performing the duplication.
        """
        self._vector_database = vector_database

    @abstractmethod
    async def aduplicate_collection(self) -> None:
        """
        Asynchronously duplicates the collection in the vector database.

        This method must be implemented by subclasses to perform the duplication
        logic specific to the target vector database.

        Returns
        -------
        None
        """
