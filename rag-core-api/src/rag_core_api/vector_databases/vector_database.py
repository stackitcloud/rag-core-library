"""Module for the VectorDatabase abstract class."""

from abc import ABC, abstractmethod

from langchain_community.vectorstores import VectorStore
from langchain_core.documents import Document

from rag_core_api.embeddings.embedder import Embedder
from rag_core_api.impl.settings.vector_db_settings import VectorDatabaseSettings


class VectorDatabase(ABC):
    """Abstract base class for a vector database."""

    def __init__(
        self,
        settings: VectorDatabaseSettings,
        embedder: Embedder,
        vectorstore: VectorStore,
    ):
        """
        Initialize the vector database.

        Parameters
        ----------
        settings : VectorDatabaseSettings
            The settings for the vector database.
        embedder : Embedder
            The embedder used to convert chunks into vector representations.
        vectorstore : Qdrant
            The Qdrant vector store instance.
        """
        self._settings = settings
        self._embedder = embedder
        self._vectorstore = vectorstore

    @property
    @abstractmethod
    def collection_available(self) -> bool:
        """Check if the collection is available in the vector database.

        Returns
        -------
        bool
            True if the collection is available, False otherwise.

        Raises
        ------
        NotImplementedError
            If the method is not implemented.
        """
        raise NotImplementedError()

    @abstractmethod
    async def asearch(self, query: str, search_kwargs: dict, filter_kwargs: dict) -> list[Document]:
        """Search in a vector database for points fitting the query and the search_kwargs.

        Parameters
        ----------
        query : str
            The search query string.
        search_kwargs : dict
            Additional keyword arguments for the search.
        filter_kwargs : dict, optional
            Optional filter keyword arguments to refine the search.

        Returns
        -------
        list[Document]
            List of langchain documents.

        Raises
        ------
        NotImplementedError
            If the method is not implemented.
        """
        raise NotImplementedError()

    @abstractmethod
    def upload(self, documents: list[Document], collection_name: str | None = None) -> None:
        """Upload the documents to the vector database.

        Parameters
        ----------
        documents : list[Document]
            List of documents which will be uploaded.
        collection_name : str, optional
            The name of the collection to upload the documents to. If None, the default collection will be used.

        Raises
        ------
        NotImplementedError
            If the method is not implemented.
        """
        raise NotImplementedError()

    @abstractmethod
    def delete(self, delete_request: dict, collection_name: str) -> None:
        """
        Delete the documents from the vector database.

        Parameters
        ----------
        delete_request : dict
            Contains the information required for deleting the documents.
        collection_name : str, optional
            The collection name to delete from; uses settings collection if None.

        Raises
        ------
        NotImplementedError
            If the method is not implemented.
        """
        raise NotImplementedError()

    @abstractmethod
    def get_collections(self) -> list[str]:
        """
        Get all collection names from the vector database.

        Returns
        -------
        list[str]
            List of all collection names.

        Raises
        ------
        NotImplementedError
            If the method is not implemented.
        """
        raise NotImplementedError()

    @abstractmethod
    def get_sorted_collection_names(self) -> list[str]:
        """
        Get sorted collection names based on the timestamp in the collection name.

        List is sorted in ascending order.

        Returns
        -------
        list[str]
            A list of sorted collection names.
        """

    @abstractmethod
    def switch_collections(self) -> None:
        """
        Switch the alias of the current collection to the specified collection.

        Raises
        ------
        NotImplementedError
            If the method is not implemented.
        """
        raise NotImplementedError()

    @abstractmethod
    def duplicate_alias_tagged_collection(self) -> None:
        """
        Duplicate the alias-tagged collection in the vector database.

        Raises
        ------
        NotImplementedError
            If the method is not implemented.
        """
        raise NotImplementedError()

