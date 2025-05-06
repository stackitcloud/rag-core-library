"""confluence_updater module

Defines an abstract base class for asynchronously updating content from Confluence.
"""

from abc import ABC, abstractmethod


class ConfluenceUpdater(ABC):
    """Interface for async Confluence content updates."""

    @abstractmethod
    async def aupdate_from_confluence(self) -> None:
        """Asynchronously fetch and update data from Confluence.

        Returns
        --------
        None
        """
