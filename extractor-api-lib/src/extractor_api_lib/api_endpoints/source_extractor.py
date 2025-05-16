from abc import ABC, abstractmethod
from typing import Optional

from extractor_api_lib.models.extraction_parameters import ExtractionParameters
from pydantic import StrictStr
from fastapi import UploadFile

from extractor_api_lib.models.information_piece import InformationPiece
from extractor_api_lib.models.key_value_pair import KeyValuePair


class SourceExtractor(ABC):

    @abstractmethod
    async def aextract_information(
        self,
        extraction_parameters: ExtractionParameters,
    ) -> list[InformationPiece]:
        """
        Extract information from source, using the given parameters.

        Parameters
        ----------
        extraction_parameters : ExtractionParameters
            The parameters used to extract information from the source.

        Returns
        -------
        list[InformationPiece]
            A list of extracted information pieces.
        """
