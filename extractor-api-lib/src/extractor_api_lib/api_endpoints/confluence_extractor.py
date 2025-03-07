"""Module for the ConfluenceExtractor abstract base class."""

from abc import ABC, abstractmethod

from extractor_api_lib.models.confluence_parameters import ConfluenceParameters
from extractor_api_lib.models.information_piece import InformationPiece


class ConfluenceExtractor(ABC):
    """Abstract base class for extract_from_confluence endpoint."""

    @abstractmethod
    async def aextract_from_confluence(self, confluence_parameters: ConfluenceParameters) -> list[InformationPiece]:
        """
        Extract information from confluence, using the given confluence parameters.

        Parameters
        ----------
        confluence_parameters : ConfluenceParameters
            The parameters used to extract information from Confluence.

        Returns
        -------
        list[InformationPiece]
            A list of extracted information pieces.
        """
