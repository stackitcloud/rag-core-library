"""Module containing the DefaultInformationPiecesUploader class."""

from fastapi import HTTPException, status

from rag_core_api.api_endpoints.information_piece_uploader import (
    InformationPiecesUploader,
)
from rag_core_api.impl.key_db.upload_counter_key_value_store import UploadCounterKeyValueStore
from rag_core_api.mapper.information_piece_mapper import InformationPieceMapper
from rag_core_api.models.information_piece import InformationPiece
from rag_core_api.vector_databases.vector_database import VectorDatabase


class DefaultInformationPiecesUploader(InformationPiecesUploader):
    """DefaultInformationPiecesUploader is responsible for uploading information pieces to a vector database."""

    def __init__(
        self,
        vector_database: VectorDatabase,
        upload_counter_key_value_store: UploadCounterKeyValueStore,
    ):
        """Initialize the DefaultInformationPiecesUploader with a vector database.

        Parameters
        ----------
        vector_database : VectorDatabase
            An instance of the VectorDatabase class used to store and manage vectors.
        upload_counter_key_value_store : UploadCOunterKeyValueStore
            The key-value store for storing the remaining operations until the underlying DB is updated.
        """
        self._vector_database = vector_database
        self._upload_counter_key_value_store = upload_counter_key_value_store

    def upload_information_piece(self, information_piece: list[InformationPiece]) -> None:
        """
        Upload a list of information pieces.

        Parameters
        ----------
        information_piece : list[InformationPiece]
            A list of InformationPiece objects to be uploaded.

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
            InformationPieceMapper.information_piece2langchain_document(document) for document in information_piece
        ]
        try:
            # TODO: check if "working" collection exists. If not create it
            self._vector_database.upload(langchain_documents)
            self._upload_counter_key_value_store.subtract()
            remaining, error = self._upload_counter_key_value_store.get()
            if not error and remaining == 0:
                # TODO: switch collection
                pass
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
