"""Module for the CollectionDuplicator abstract base class."""

from abc import ABC, abstractmethod

#TODO: add doc strings, revise accordingly

class CollectionDuplicator(ABC):


    @abstractmethod
    async def aduplicate_collection(self) -> None:
        ...
