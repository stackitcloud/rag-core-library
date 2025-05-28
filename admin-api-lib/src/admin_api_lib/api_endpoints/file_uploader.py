"""Module for the upload file endpoint."""

from abc import ABC, abstractmethod
from typing import Optional

from fastapi import UploadFile


class FileUploader(ABC):

    @abstractmethod
    async def upload_file(
        self,
        base_url: str,
        file: UploadFile,
        timeout: Optional[float],
    ) -> None:
        """
        Uploads a source file for content extraction.

        Parameters
        ----------
        base_url : str
            The base url of the service. Is used to determine the download link of the file.
        file : UploadFile
            The file to process.
        timeout : float, optional
          Timeout for the operation.

        Returns
        -------
        None
        """
