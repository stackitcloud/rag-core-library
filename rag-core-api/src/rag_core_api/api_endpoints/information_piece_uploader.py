"""Module for the InformationPiecesUploader abstract base class."""

from abc import ABC, abstractmethod

from rag_core_api.models.upload_request import UploadRequest


class InformationPiecesUploader(ABC):
    """Abstract base class for uploading information pieces.

    This class defines the interface for uploading a list of information pieces.
    """

    @abstractmethod
    def upload_information_piece(self, upload_request: UploadRequest) -> None:
        """
        Abstract method to upload a list of information pieces.

        Parameters
        ----------
        upload_request : UploadRequest
            The upload request containing a list of InformationPiece objects to be uploaded and a boolean value,
            determining if the latest collection, or the one with the desired alias should be used.

        Returns
        -------
        None
        """
