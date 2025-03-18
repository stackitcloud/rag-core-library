"""Module for the CollectionSwitcher abstract base class."""

from abc import ABC, abstractmethod

#TODO: add doc strings, revise accordingly

class CollectionSwitcher(ABC):


    @abstractmethod
    async def aswitch_collection(self) -> None:
        ...
