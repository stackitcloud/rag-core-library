"""Module for the DefaultFileExtractor class."""

import logging
from typing import Optional

from extractor_api_lib.models.extraction_parameters import ExtractionParameters
from pydantic import StrictStr
from fastapi import UploadFile

from extractor_api_lib.extractors.information_extractor import InformationExtractor
from extractor_api_lib.models.information_piece import InformationPiece
from extractor_api_lib.models.key_value_pair import KeyValuePair
from extractor_api_lib.impl.mapper.internal2external_information_piece import Internal2ExternalInformationPiece
from extractor_api_lib.api_endpoints.source_extractor import SourceExtractor
from extractor_api_lib.impl.mapper.internal2external_information_piece import Internal2ExternalInformationPiece
from extractor_api_lib.models.information_piece import InformationPiece
from extractor_api_lib.models.key_value_pair import KeyValuePair
from extractor_api_lib.impl.types.extractor_types import ExtractorTypes
from extractor_api_lib.models.dataclasses.internal_information_piece import InternalInformationPiece


logger = logging.getLogger(__name__)


class GeneralSourceExtractor(SourceExtractor):
    """A class to extract information from documents using available extractors.

    This class serves as a general extractor that utilizes a list of available
    information extractors to extract content from documents. It determines the
    appropriate extractor based on the file type of the document.
    """

    def __init__(self, available_extractors: list[InformationExtractor], mapper: Internal2ExternalInformationPiece):
        """
        Initialize the GeneralExtractor.

        Parameters
        ----------
        available_extractors : list of InformationExtractor
            A list of available information extractors to be used by the GeneralExtractor.
        """
        self._mapper = mapper
        self._available_extractors = available_extractors

    async def aextract_information(
        self,
        extraction_parameters: ExtractionParameters,
    ) -> list[InformationPiece]:
        """
        Extract content from given file.

        Parameters
        ----------
        file_path : Path
            Path to the file the information should be extracted from.

        Returns
        -------
        list[InformationPiece]
            The extracted information.
        """
        correct_extractors = [x for x in self._available_extractors if extraction_parameters.type == x.extractor_type]
        if not correct_extractors:
            raise ValueError(f"No extractor found for type {type}")
        results = await correct_extractors[-1].aextract_content(extraction_parameters)
        return [self._mapper.map_internal_to_external(x) for x in results if x.page_content is not None]
