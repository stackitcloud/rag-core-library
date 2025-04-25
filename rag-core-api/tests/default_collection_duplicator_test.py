import os

import pytest
from qdrant_client import QdrantClient, models
from rag_core_lib.impl.utils.timestamp_creator import create_timestamp

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

    yield client


def test_my(qdrant_client: QdrantClient) -> None:
    """
    Test the Qdrant client.
    """
    collection_alias_name = os.environ.get("VECTOR_DB_COLLECTION_NAME")
    collection_name = qdrant_client.get_collections().collections[0].name
    assert qdrant_client.get_collection(collection_name) is not None

    points = qdrant_client.scroll(
        collection_name=collection_name,
        limit=3,
        offset=0,
    )[0]
    assert len(points) == 3
    assert points[0].id == 1
    assert points[1].id == 2
    assert points[2].id == 3

    points = qdrant_client.scroll(
        collection_name=collection_alias_name,
        limit=3,
        offset=0,
    )[0]
    assert len(points) == 3
    assert points[0].id == 1 and points[1].id == 2 and points[2].id == 3
