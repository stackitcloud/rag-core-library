import logging
from time import sleep

import pytest
from rag_core_api.api_endpoints.collection_switcher import CollectionSwitcher
from rag_core_api.api_endpoints.collection_duplicator import CollectionDuplicator
from qdrant_client import QdrantClient, models

from rag_core_api.impl.api_endpoints.default_collection_switcher import DefaultCollectionSwitcher
from rag_core_api.vector_databases.vector_database import VectorDatabase


@pytest.fixture
def collection_switcher(vector_database: VectorDatabase) -> CollectionSwitcher:
    return DefaultCollectionSwitcher(vector_database)


@pytest.mark.asyncio
async def test_aswitch_collection(
    collection_duplicator: CollectionDuplicator, collection_switcher: CollectionSwitcher
) -> None:
    qdrant_client: QdrantClient = collection_duplicator._vector_database._vectorstore.client
    collections = qdrant_client.get_collections().collections
    assert len(collections) == 1
    sleep(1)  # necessary, otherwise the collections share the same names.
    await collection_duplicator.aduplicate_collection()
    collections = qdrant_client.get_collections().collections
    assert len(collections) > 1

    collection_name = collection_duplicator._vector_database.get_sorted_collection_names()[-1]

    point = models.PointStruct(
        id=1,
        payload={
            "color": "pink",
        },
        vector=[0.9, 0.3141, 0.1],
    )
    qdrant_client.upsert(
        collection_name=collection_name,
        points=[
            point,
        ],
    )

    aliases_old = qdrant_client.get_aliases().aliases
    await collection_switcher.aswitch_collection()
    aliases_new = qdrant_client.get_aliases().aliases

    assert aliases_old[0].collection_name != aliases_new[0].collection_name
    collections = qdrant_client.get_collections().collections
    assert len(collections) == 1

    point_oi = qdrant_client.scroll(
        collection_name=aliases_new[0].alias_name,
        scroll_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key=list(point.payload.keys())[0], match=models.MatchValue(value=list(point.payload.values())[0])
                )
            ]
        ),
        limit=1,
        with_vectors=True,
    )
    assert point_oi[0][0].payload["color"] == point.payload["color"]
    assert (
        point_oi[0][0].vector != point.vector
    )  # This should be the same, issue is opened. https://github.com/qdrant/qdrant-client/issues/982
    assert point_oi[0][0].id == point.id


@pytest.mark.asyncio
async def test_aswitch_collection_without_duplication(
    collection_duplicator: CollectionDuplicator,
    collection_switcher: CollectionSwitcher,
    caplog: pytest.LogCaptureFixture,
) -> None:
    qdrant_client = collection_duplicator._vector_database._vectorstore.client
    collections = qdrant_client.get_collections().collections
    assert len(collections) == 1

    aliases_old = qdrant_client.get_aliases().aliases

    with caplog.at_level(logging.WARNING):
        await collection_switcher.aswitch_collection()

    aliases_new = qdrant_client.get_aliases().aliases

    assert aliases_old[0].collection_name == aliases_new[0].collection_name

    assert any(
        "Nothings needs to be done, alias already set for the collection!" in record.message
        for record in caplog.records
    )
