from abc import ABC, abstractmethod
from typing import Optional

from pydantic import StrictStr
from fastapi import UploadFile

from extractor_api_lib.models.information_piece import InformationPiece
from extractor_api_lib.models.key_value_pair import KeyValuePair


class Extractor(ABC):

    @abstractmethod
    async def aextract_information(
        self,
        type: StrictStr,
        name: StrictStr,
        file: Optional[UploadFile],
        kwargs: Optional[list[KeyValuePair]],
    ) -> list[InformationPiece]:
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
