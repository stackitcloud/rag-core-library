# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import Field, StrictBytes, StrictStr
from typing import Any, List, Tuple, Union
from typing_extensions import Annotated
from fastapi import Request, Response, UploadFile

from admin_api_lib.models.document_status import DocumentStatus
from admin_api_lib.models.upload_source import UploadSource


class BaseAdminApi:
    """
    The base AdminApi interface.

    Attributes
    ----------
    subclasses : ClassVar[Tuple]
        A tuple that holds all subclasses of BaseAdminApi.
    """

    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseAdminApi.subclasses = BaseAdminApi.subclasses + (cls,)

    async def delete_document(
        self,
        identification: StrictStr,
    ) -> None:
        """
        Asynchronously deletes a document based on the provided identification.

        Parameters
        ----------
        identification : str
            The unique identifier of the document to be deleted.

        Returns
        -------
        None
        """


    async def document_reference_id_get(
        self,
        identification: str,
    ) -> Response:
        """
        Asynchronously retrieve a document reference by its identification.

        Parameters
        ----------
        identification : str
            The unique identifier for the document reference.

        Returns
        -------
        Response
            The response object containing the document reference details.
        """


    async def get_all_documents_status(
        self,
    ) -> list[DocumentStatus]:
        """
        Asynchronously retrieves the status of all documents.

        Returns
        -------
        list[DocumentStatus]
            A list containing the status of all documents.
        """


    async def upload_source(
        self,
        upload_source: Annotated[UploadSource, Field(description="The PDF document to upload.")],
    ) -> None:
        ...
