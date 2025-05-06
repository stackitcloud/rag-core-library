"""Module containing the QdrantDatabase class."""

from datetime import datetime
import logging

from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore, SparseEmbeddings
from qdrant_client.http import models
from qdrant_client.models import FieldCondition, Filter, MatchValue

from rag_core_api.embeddings.embedder import Embedder
from rag_core_api.impl.settings.vector_db_settings import VectorDatabaseSettings
from rag_core_api.vector_databases.vector_database import VectorDatabase
from rag_core_lib.impl.utils.timestamp_creator import create_timestamp


logger = logging.getLogger(__name__)


class QdrantDatabase(VectorDatabase):
    """
    A class representing the interface to the Qdrant database.

    Inherits from VectorDatabase.
    """

    def __init__(
        self,
        settings: VectorDatabaseSettings,
        embedder: Embedder,
        sparse_embedder: SparseEmbeddings,
        vectorstore: QdrantVectorStore,
    ):
        """
        Initialize the Qdrant database.

        Parameters
        ----------
        settings : VectorDatabaseSettings
            The settings for the vector database.
        embedder : Embedder
            The embedder used to convert chunks into vector representations.
        vectorstore : Qdrant
            The Qdrant vector store instance.
        """
        super().__init__(
            settings=settings,
            embedder=embedder,
            vectorstore=vectorstore,
            sparse_embedder=sparse_embedder,
        )

    @property
    def collection_available(self):
        """
        Check if the collection is available and has points.

        This property checks if the collection specified by the `_vectorstore.collection_name`
        exists in the list of collections and if it contains any points.

        Returns
        -------
        bool
            True if the collection exists and has points, False otherwise.
        """
        if self._vectorstore.collection_name in [c.name for c in self.get_collections()]:
            collection = self._vectorstore.client.get_collection(self._vectorstore.collection_name)
            return collection.points_count > 0
        return False

    @staticmethod
    def _search_kwargs_builder(search_kwargs: dict, filter_kwargs: dict):
        """Build search kwargs with proper Qdrant filter format."""
        if not filter_kwargs:
            return search_kwargs

        # Convert dict filter to Qdrant filter format
        qdrant_filter = models.Filter(
            must=[
                models.FieldCondition(key="metadata." + key, match=models.MatchValue(value=value))
                for key, value in filter_kwargs.items()
            ]
        )

        return {**search_kwargs, "filter": qdrant_filter}

    async def asearch(self, query: str, search_kwargs: dict, filter_kwargs: dict | None = None) -> list[Document]:
        """
        Asynchronously search for documents based on a query and optional filters.

        Parameters
        ----------
        query : str
            The search query string.
        search_kwargs : dict
            Additional keyword arguments for the search.
        filter_kwargs : dict, optional
            Optional filter keyword arguments to refine the search (default is None).

        Returns
        -------
        list[Document]
            A list of documents that match the search query and filters, including related documents.
        """
        try:
            search_params = self._search_kwargs_builder(search_kwargs=search_kwargs, filter_kwargs=filter_kwargs)

            retriever = self._vectorstore.as_retriever(query=query, search_kwargs=search_params)

            results = await retriever.ainvoke(query)
            related_results = []

            for res in results:
                related_results += self._get_related(res.metadata["related"])
            return results + related_results

        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            raise

    def get_specific_document(self, document_id: str) -> list[Document]:
        """
        Retrieve a specific document from the vector database using the document ID.

        Parameters
        ----------
        document_id : str
            The ID of the document to retrieve.

        Returns
        -------
        list[Document]
            A list containing the requested document as a Document object. If the document is not found,
            an empty list is returned.
        """
        requested = self._vectorstore.client.scroll(
            collection_name=self._vectorstore.collection_name,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="metadata.id",
                        match=MatchValue(value=document_id),
                    )
                ]
            ),
        )
        if not requested:
            return []
        # convert to Document
        return [
            (
                Document(
                    page_content=search_result.payload["page_content"],
                    metadata=search_result.payload["metadata"],
                )
            )
            for search_result in requested[0]
        ]

    def upload(self, documents: list[Document], collection_name: str | None = None) -> None:
        """
        Save the given documents to the Qdrant database. If collection does not exist, it will be created.

        Parameters
        ----------
        documents : list[Document]
            The list of documents to be stored.
        collection_name : str, optional
            The name of the collection to store the documents in; uses settings collection if None.

        Returns
        -------
        None
        """

        alias_of_interest = self._get_aliases_of_interest()
        if collection_name:
            true_collection_name = collection_name
        elif not len(alias_of_interest):
            true_collection_name = self._settings.collection_name + f"_{create_timestamp()}"
        else:
            true_collection_name = alias_of_interest[0].collection_name

        self._vectorstore = self._vectorstore.from_documents(
            documents,
            collection_name=true_collection_name,
            embedding=self._embedder.get_embedder(),
            sparse_embedding=self._sparse_embedder,
            location=self._settings.location,
            retrieval_mode=self._settings.retrieval_mode,
        )

        if len(alias_of_interest) == 0:
            self._vectorstore.client.update_collection_aliases(
                change_aliases_operations=[
                    models.CreateAliasOperation(
                        create_alias=models.CreateAlias(
                            collection_name=true_collection_name, alias_name=self._settings.collection_name
                        )
                    ),
                ]
            )

    def delete(self, delete_request: dict, collection_name: str | None = None) -> None:
        """
        Delete points from a collection based on the given conditions.

        Parameters
        ----------
        delete_request : dict
            Conditions to match the points to be deleted.
        collection_name : str, optional
            The collection name to delete from; uses settings collection if None.
        """
        alias_of_interest = self._get_aliases_of_interest()
        if collection_name:
            true_collection_name = collection_name
        elif len(alias_of_interest):
            true_collection_name = alias_of_interest[0].collection_name
        else:
            raise ValueError(f"Collection with alias {self._settings.collection_name} does not exist.")

        filter_conditions = [
            models.FieldCondition(
                key=key,
                match=models.MatchValue(value=value),
            )
            for key, value in delete_request.items()
        ]

        points_selector = models.FilterSelector(
            filter=models.Filter(
                must=filter_conditions,
            )
        )

        self._vectorstore.client.delete(
            collection_name=true_collection_name,
            points_selector=points_selector,
        )

    def get_collections(self) -> list[str]:
        """
        Get all collection names from the vector database.

        Returns
        -------
        list[str]
            A list of collection names from the vector database.
        """
        return self._vectorstore.client.get_collections().collections

    def switch_collections(self, collection_name: str):
        """
        Switch the alias of the current collection to the specified collection.


        Parameters
        ----------
        collection_name : str
            The name of the collection to switch to.
        """
        aliases = self._vectorstore.client.get_aliases().aliases
        for alias in aliases:
            if alias.alias_name == self._settings.collection_name:
                if alias.collection_name == collection_name:
                    logger.warning("Nothings needs to be done, alias already set for the collection!")
                break

        self._vectorstore.client.update_collection_aliases(
            change_aliases_operations=[
                models.DeleteAliasOperation(delete_alias=models.DeleteAlias(alias_name=self._settings.collection_name)),
                models.CreateAliasOperation(
                    create_alias=models.CreateAlias(
                        collection_name=collection_name, alias_name=self._settings.collection_name
                    )
                ),
            ]
        )

        self._cleanup_old_collections()

    def create_collection_from(self, source_collection_name: str, target_collection_name: str):
        """
        Create a new collection from an existing collection.

        Parameters
        ----------
        source_collection_name : str
            The name of the source collection.
        target_collection_name : str
            The name of the target collection.
        """
        self._vectorstore.client.create_collection(
            collection_name=target_collection_name,
            vectors_config=self._vectorstore.client.get_collection(source_collection_name).config.params.vectors,
            sparse_vectors_config=self._vectorstore.client.get_collection(
                source_collection_name
            ).config.params.sparse_vectors,
            init_from=models.InitFrom(collection=source_collection_name),
        )

    def duplicate_alias_tagged_collection(self):
        """
        Duplicate the latest collection in the database.

        This method creates a new collection with the same configuration as the latest collection
        and copies all points from the latest collection to the new one.
        """
        aliases = self._vectorstore.client.get_aliases()
        alias_of_interest = []
        for alias in aliases.aliases:
            if alias.alias_name == self._settings.collection_name:
                alias_of_interest.append(alias)
        if len(alias_of_interest) == 0:
            raise ValueError(f"Collection with alias {self._settings.collection_name} does not exist.")
        if len(alias_of_interest) > 1:
            raise ValueError(f"Multiple collections with alias {self._settings.collection_name} exist.")

        source_collection_name = alias_of_interest[0].collection_name
        target_collection_name = f"{alias_of_interest[0].alias_name}_{create_timestamp()}"

        logger.info(f"Duplicating collection {source_collection_name} to {target_collection_name}")
        self.create_collection_from(
            source_collection_name=source_collection_name, target_collection_name=target_collection_name
        )

    def get_sorted_collection_names(self) -> list[str]:
        """
        Get sorted collection names based on the timestamp in the collection name.

        List is sorted in ascending order.

        Returns
        -------
        list[str]
            A list of sorted collection names.
        """
        collections = self.get_collections()
        collection_alias_name = self._settings.collection_name
        collections_names = []
        for collection in collections:
            if collection.name.startswith(collection_alias_name):
                collections_names.append(collection.name)
        if not collections_names:
            raise ValueError(f"No collections found with alias {collection_alias_name}.")
        if len(collections_names) == 1:
            return collections_names
        return sorted(collections_names, key=lambda x: datetime.strptime(x.rsplit("_", 1)[-1], "%Y%m%d%H%M%S"))

    def _get_aliases_of_interest(self) -> list:
        aliases = self._vectorstore.client.get_aliases()
        alias_of_interest = []
        for alias in aliases.aliases:
            if alias.alias_name == self._settings.collection_name:
                alias_of_interest.append(alias)
        return alias_of_interest

    def _get_related(self, related_ids: list[str]) -> list[Document]:
        result = []
        for document_id in related_ids:
            result += self.get_specific_document(document_id)
        return result

    def _delete_collection(self, collection_name: str) -> None:
        """
        Delete a collection from the vector database.

        Parameters
        ----------
        collection_name : str
            The name of the collection to be deleted.

        Returns
        -------
        None
        """
        self._vectorstore.client.delete_collection(collection_name=collection_name)

    def _cleanup_old_collections(self):
        """Clean up old collections in the vector database."""
        sorted_collections = self.get_sorted_collection_names()
        nr_collections = len(sorted_collections)
        if nr_collections == 1 or nr_collections < self._settings.collection_history_count:
            return

        logging.info(
            f"""Found {nr_collections} collections, but only {self._settings.collection_history_count} are allowed.
            Cleaning up..."""
        )

        while nr_collections > self._settings.collection_history_count:
            # delete the oldest collection
            collection_to_delete = sorted_collections[0]
            self._delete_collection(collection_to_delete)
            sorted_collections.pop(0)
            nr_collections = len(sorted_collections)
            logger.info(f"Deleted collection: {collection_to_delete}")
