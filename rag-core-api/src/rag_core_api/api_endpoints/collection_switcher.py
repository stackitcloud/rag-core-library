"""Module for the CollectionSwitcher abstract base class."""

from abc import ABC, abstractmethod

from rag_core_api.vector_databases.vector_database import VectorDatabase


class CollectionSwitcher(ABC):
    """Abstract base class for switching collections in a vector database."""

    def __init__(self, vector_database: VectorDatabase):
        """
        Initialize the CollectionSwitcher with a vector database.

        Parameters
        ----------
        vector_database : VectorDatabase
            The vector database instance to use for performing switch of the collections.
        """
        self._vector_database = vector_database

    @abstractmethod
    async def aswitch_collection(self) -> None:
        """Asynchronously switch to the latest collection.

        Retrieves the name of the most recently created collection from the
        vector database and performs the switch.

        Returns
        -------
        None
        """
