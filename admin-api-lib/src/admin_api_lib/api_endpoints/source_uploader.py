"""Module for the upload source endpoint."""

from abc import ABC, abstractmethod
from typing import Optional

from pydantic import StrictStr

from admin_api_lib.models.key_value_pair import KeyValuePair


class SourceUploader(ABC):
    """Abstract base class for source upload."""

    @abstractmethod
    async def upload_source(
        self,
        source_type: StrictStr,
        name: StrictStr,
        kwargs: list[KeyValuePair],
        timeout: Optional[float],
    ) -> None:
        """
        Uploads the parameters for source content extraction.

        Parameters
        ----------
        source_type : str
            The type of the source. Is used by the extractor service to determine the correct extraction method.
        name : str
            Display name of the source.
        kwargs : list[KeyValuePair]
            List of KeyValuePair with parameters used for the extraction.
        timeout : float, optional
            Timeout for the operation.

        Returns
        -------
        None
        """
