"""Module containing the UploadCounterKeyValueStore class."""

import json
import logging

from redis import Redis

from admin_api_lib.impl.settings.key_value_settings import KeyValueSettings
from admin_api_lib.models.status import Status


logger = logging.getLogger(__name__)


class UploadCounterKeyValueStore:
    """
    A key-value store for managing file statuses using Redis.

    This class provides methods for adding and subtracting remaining upload operations from a Redis store.

    Attributes
    ----------
    STORAGE_KEY : str
        The key under which the counter of remaining operations for upload stored in Redis.
    FAILURE_STORAGE_KEY : str
        The key under which the failure state of the upload is stored in Redis.
    """

    STORAGE_KEY = "stackit-rag-template-upload-counter"
    FAILURE_STORAGE_KEY = "stackit-rag-template-upload-failure"

    def __init__(self, settings: KeyValueSettings):
        """
        Initialize the UploadCounterKeyValueStore with the given settings.

        Parameters
        ----------
        settings : KeyValueSettings
            The settings object containing the host and port information for the Redis connection.
        """
        self._redis = Redis(host=settings.host, port=settings.port, decode_responses=True)
        self._expiration = settings.expiration
        # TODO: set failure to True if expiration event occurs

    def add(self, counter: int) -> None:
        """
        Adds the number of operations to the key-value store.

        Parameters
        ----------
        counter : int
            The additional operations that are required to fully upload a source.

        Returns
        -------
        None
        """
        pipe = self._redis.pipeline()
        pipe.incrby(UploadCounterKeyValueStore.STORAGE_KEY, counter)
        pipe.expire(UploadCounterKeyValueStore.STORAGE_KEY, self._expiration)

        try:
            # Attempt to execute the transaction
            pipe.execute()

        except Exception as e:
            logger.error(e)
            self._redis.set(UploadCounterKeyValueStore.FAILURE_STORAGE_KEY, True)

    def subtract(self, counter: int = 1) -> None:
        """
        Subtract the specified number of operations from the key-value store.

        Parameters
        ----------
        counter : int
            The number of operations that have been performed. Defaults to 1

        Returns
        -------
        None
        """
        pipe = self._redis.pipeline()
        pipe.decrby(UploadCounterKeyValueStore.STORAGE_KEY, counter)

        try:
            # Attempt to execute the transaction
            pipe.execute()

        except Exception as e:
            logger.error(e)

    def get(self) -> tuple[int, bool]:
        """
        Retrieves the remaining number of operations, as well as the failure state from the Redis store.

        Returns
        -------
        tuple[int, bool]
            The number of remaining operations, failure occured
        """
        return self._redis.get(UploadCounterKeyValueStore.STORAGE_KEY), self._redis.get(
            UploadCounterKeyValueStore.FAILURE_STORAGE_KEY
        )
