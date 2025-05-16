"""Module for the Base class for Information extractors."""

from abc import ABC, abstractmethod
from typing import Optional


from extractor_api_lib.models.extraction_parameters import ExtractionParameters
from fastapi import UploadFile
from pydantic import StrictStr

from extractor_api_lib.impl.types.extractor_types import ExtractorTypes
from extractor_api_lib.models.information_piece import InformationPiece
from extractor_api_lib.models.key_value_pair import KeyValuePair
from extractor_api_lib.models.dataclasses.internal_information_piece import InternalInformationPiece


class InformationExtractor(ABC):
    """Base class for Information extractors."""

    @property
    @abstractmethod
    def extractor_type(self) -> ExtractorTypes: ...

    @abstractmethod
    async def aextract_content(
        self,
         extraction_parameters: ExtractionParameters,
    ) -> list[InternalInformationPiece]:
        """
        Extract content from source.

        Parameters
        ----------
        extraction_parameters : ExtractionParameters
            The parameters used to extract information from the source.

        Returns
        -------
        list[InformationPiece]
            The extracted information.
        """
