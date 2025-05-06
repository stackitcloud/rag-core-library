import os
import sys

from langchain_qdrant import QdrantVectorStore
import pytest
from qdrant_client import QdrantClient, models
from rag_core_api.api_endpoints.collection_duplicator import CollectionDuplicator
from rag_core_api.impl.api_endpoints.default_collection_duplicator import DefaultCollectionDuplicator
from rag_core_api.impl.settings.fake_embedder_settings import FakeEmbedderSettings
from rag_core_api.impl.settings.vector_db_settings import VectorDatabaseSettings
from rag_core_api.impl.vector_databases.qdrant_database import QdrantDatabase
from rag_core_api.vector_databases.vector_database import VectorDatabase
from rag_core_lib.impl.utils.timestamp_creator import create_timestamp
from langchain_community.embeddings import FakeEmbeddings

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mock_environment_variables import mock_environment_variables

mock_environment_variables()


@pytest.fixture
def qdrant_client() -> QdrantClient:
    """
    Mock Qdrant client for testing.
    """
    client = QdrantClient(os.environ.get("VECTOR_DB_LOCATION"), vectors_config={"size": 3})
    collection_alias = os.environ.get("VECTOR_DB_COLLECTION_NAME")
    collection_name = f"{collection_alias}_{create_timestamp()}"
    try:
        client.create_collection(
            collection_name, vectors_config=models.VectorParams(size=3, distance=models.Distance.COSINE)
        )
    except Exception as e:
        print(f"Collection already exists: {e}")

    client.upsert(
        collection_name=collection_name,
        points=[
            models.PointStruct(
                id=1,
                payload={
                    "color": "red",
                },
                vector=[0.9, 0.1, 0.1],
            ),
            models.PointStruct(
                id=2,
                payload={
                    "color": "green",
                },
                vector=[0.1, 0.9, 0.1],
            ),
            models.PointStruct(
                id=3,
                payload={
                    "color": "blue",
                },
                vector=[0.1, 0.1, 0.9],
            ),
        ],
    )

    client.update_collection_aliases(
        change_aliases_operations=[
            models.CreateAliasOperation(
                create_alias=models.CreateAlias(
                    alias_name=collection_alias,
                    collection_name=collection_name,
                )
            )
        ],
    )

    return client


@pytest.fixture
def vector_database(qdrant_client: QdrantClient) -> VectorDatabase:
    settings = VectorDatabaseSettings()
    embedder_settings = FakeEmbedderSettings()
    embedder = FakeEmbeddings(**embedder_settings.model_dump())
    vectorstore = QdrantVectorStore(qdrant_client, settings.collection_name, embedding=embedder)

    return QdrantDatabase(settings=settings, embedder=embedder, sparse_embedder=embedder, vectorstore=vectorstore)


@pytest.fixture
def collection_duplicator(vector_database: VectorDatabase) -> CollectionDuplicator:
    return DefaultCollectionDuplicator(vector_database=vector_database)
