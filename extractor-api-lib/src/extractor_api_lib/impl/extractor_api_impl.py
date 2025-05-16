"""Module for the implementation of the ExtractorApi interface."""

from dependency_injector.wiring import Provide, inject
from extractor_api_lib.api_endpoints.file_extractor import FileExtractor
from extractor_api_lib.api_endpoints.source_extractor import SourceExtractor
from extractor_api_lib.models.extraction_parameters import ExtractionParameters
from extractor_api_lib.models.extraction_request import ExtractionRequest
from fastapi import Depends, UploadFile

from pydantic import StrictStr
from typing import Optional
from extractor_api_lib.models.information_piece import InformationPiece
from extractor_api_lib.models.key_value_pair import KeyValuePair

from extractor_api_lib.apis.extractor_api_base import BaseExtractorApi
from extractor_api_lib.dependency_container import DependencyContainer
from extractor_api_lib.models.information_piece import InformationPiece


class ExtractorApiImpl(BaseExtractorApi):
    """Implementation of the ExtractorApi interface."""

    @inject
    async def extract_from_file_post(
        self,
        extraction_request: ExtractionRequest,
        extractor: FileExtractor = Depends(Provide[DependencyContainer.general_file_extractor]),
    ) -> list[InformationPiece]:
        return await extractor.aextract_information(extraction_request)

    async def extract_from_source(
        self,
        extraction_parameters: ExtractionParameters,
        extractor: SourceExtractor = Depends(Provide[DependencyContainer.source_extractor]),
    ) -> list[InformationPiece]:
        return await extractor.aextract_information(extraction_parameters)
