"""Module for the Base class for Information extractors."""

from abc import ABC, abstractmethod
from typing import Optional


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
        type: StrictStr,
        name: StrictStr,
        file: Optional[UploadFile],
        kwargs: Optional[list[KeyValuePair]],
    ) -> list[InternalInformationPiece]:
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
