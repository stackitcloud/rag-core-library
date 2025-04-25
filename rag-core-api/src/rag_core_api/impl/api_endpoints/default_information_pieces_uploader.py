"""Module containing the DefaultInformationPiecesUploader class."""

from fastapi import HTTPException, status

from rag_core_api.api_endpoints.information_piece_uploader import (
    InformationPiecesUploader,
)
from rag_core_api.mapper.information_piece_mapper import InformationPieceMapper
from rag_core_api.models.upload_request import UploadRequest
from rag_core_api.vector_databases.vector_database import VectorDatabase


class DefaultInformationPiecesUploader(InformationPiecesUploader):
    """DefaultInformationPiecesUploader is responsible for uploading information pieces to a vector database."""

    def __init__(self, vector_database: VectorDatabase):
        """Initialize the DefaultInformationPiecesUploader with a vector database.

        Parameters
        ----------
        vector_database : VectorDatabase
            An instance of the VectorDatabase class used to store and manage vectors.
        """
        self._vector_database = vector_database

    def upload_information_piece(self, upload_request: UploadRequest) -> None:
        """
        Upload a list of information pieces.

        Parameters
        ----------
        upload_request : UploadRequest
            The upload request containing a list of InformationPiece objects to be uploaded and a boolean value,
            determining if the latest collection, or the one with the desired alias should be used.

        Raises
        ------
        HTTPException
            If there is a ValueError, raises an HTTP 422 Unprocessable Entity error.
            If there is any other exception, raises an HTTP 500 Internal Server Error.

        Returns
        -------
        None
        """
        langchain_documents = [
            InformationPieceMapper.information_piece2langchain_document(document) for document in upload_request.information_pieces
        ]
        collection_name = None
        if upload_request.use_latest_collection:
            collection_name = self._vector_database.get_sorted_collection_names()[0]

        try:
            self._vector_database.upload(langchain_documents, collection_name=collection_name)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
