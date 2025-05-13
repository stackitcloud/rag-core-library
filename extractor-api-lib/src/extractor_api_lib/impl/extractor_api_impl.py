"""Module for the implementation of the ExtractorApi interface."""

from dependency_injector.wiring import Provide, inject
from extractor_api_lib.api_endpoints.extractor import Extractor
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
    async def extract(
        self,
        type: StrictStr,
        name: StrictStr,
        file: Optional[UploadFile],
        kwargs: Optional[list[KeyValuePair]],
        extractor: Extractor = Depends(Provide[DependencyContainer.default_extractor]),
    ) -> list[InformationPiece]:
        """
        Extract information from a source.

        Parameters
        ----------
        extraction_request : ExtractionRequest
            The request containing details about the extraction process.
        file_extractor : FileExtractor, optional
            The file extractor dependency, by default Depends(Provide[DependencyContainer.file_extractor]).

        Returns
        -------
        list[InformationPiece]
            A list of extracted information pieces.
        """
        return await extractor.aextract_information(type, name, file, kwargs)
