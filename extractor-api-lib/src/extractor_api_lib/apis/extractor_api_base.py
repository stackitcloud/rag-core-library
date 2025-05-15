# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from typing import Any, List
from extractor_api_lib.models.extraction_parameters import ExtractionParameters
from extractor_api_lib.models.extraction_request import ExtractionRequest
from extractor_api_lib.models.information_piece import InformationPiece


class BaseExtractorApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseExtractorApi.subclasses = BaseExtractorApi.subclasses + (cls,)

    async def extract_from_file_post(
        self,
        extraction_request: ExtractionRequest,
    ) -> List[InformationPiece]: ...

    async def extract_from_source(
        self,
        extraction_parameters: ExtractionParameters,
    ) -> List[InformationPiece]: ...
