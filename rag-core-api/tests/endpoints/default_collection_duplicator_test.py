import os
from time import sleep

import pytest
from rag_core_api.api_endpoints.collection_duplicator import CollectionDuplicator


def test_qdrant_client(qdrant_client)->None:
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

@pytest.mark.asyncio
async def test_aduplicate_collection(collection_duplicator:CollectionDuplicator)->None:
    qdrant_client = collection_duplicator._vector_database._vectorstore.client
    collections = qdrant_client.get_collections().collections
    assert len(collections)==1
    sleep(1) #necessary, otherwise the collections share the same names.
    await collection_duplicator.aduplicate_collection()
    collections = qdrant_client.get_collections().collections
    assert len(collections)>1
