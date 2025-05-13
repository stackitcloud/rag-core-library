"""Module for the GeneralExtractor class."""

import logging
from pathlib import Path
import tempfile
import traceback
from typing import Any, List, Optional


from pydantic import StrictStr
from fastapi import UploadFile

from extractor_api_lib.file_services.file_service import FileService
from extractor_api_lib.extractors.information_file_extractor import InformationFileExtractor
from extractor_api_lib.extractors.information_extractor import InformationExtractor
from extractor_api_lib.impl.types.extractor_types import ExtractorTypes
from extractor_api_lib.models.information_piece import InformationPiece
from extractor_api_lib.models.key_value_pair import KeyValuePair
from extractor_api_lib.models.dataclasses.internal_information_piece import InternalInformationPiece

logger = logging.getLogger(__name__)


class GeneralFileExtractor(InformationExtractor):
    """A class to extract information from documents using available extractors.

    This class serves as a general extractor that utilizes a list of available
    information extractors to extract content from documents. It determines the
    appropriate extractor based on the file type of the document.
    """

    def __init__(self, file_service: FileService, available_extractors: list[InformationFileExtractor]):
        """
        Initialize the GeneralExtractor.

        Parameters
        ----------
        file_service : FileService
            An instance of FileService to handle file operations.
        available_extractors : list of InformationExtractor
            A list of available information extractors to be used by the GeneralExtractor.
        """
        self._file_service=file_service
        self._available_extractors = available_extractors

    @property
    def extractor_type(self) -> ExtractorTypes:
        return ExtractorTypes.FILE

    async def aextract_content(
        self,
        type: StrictStr,
        name: StrictStr,
        file: Optional[UploadFile],
        kwargs: Optional[List[KeyValuePair]],
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
        # save file on s3
        content = await file.read()
        filename = file.filename
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_file_path = Path(temp_dir) / filename
                with open(temp_file_path, "wb") as temp_file:
                    logger.debug("Temporary file created at %s.", temp_file_path)
                    temp_file.write(content)
                    logger.debug("Temp file created and content written.")
                self._file_service.upload_file(temp_file_path, filename)
                file_type = str(temp_file_path).split(".")[-1].upper()
                correct_extractors = [
                    x for x in self._available_extractors if file_type in [y.value for y in x.compatible_file_types]
                ]
                if not correct_extractors:
                    raise ValueError(f"No extractor found for file-ending {file_type}")
                return await correct_extractors[-1].aextract_content(temp_file_path)
        except Exception as e:
            logger.error("Error during document parsing: %s %s", e, traceback.format_exc())
            raise e
