# coding: utf-8

from typing import Dict, List, Annotated  # noqa: F401
import importlib
import pkgutil

from admin_api_lib.apis.admin_api_base import BaseAdminApi
from fastapi import APIRouter, Path, Request, Response, UploadFile, Form  # noqa: F401

import admin_api_lib.impl

from fastapi import (  # noqa: F401
    APIRouter,
    Body,
    Cookie,
    Depends,
    Form,
    Header,
    HTTPException,
    Path,
    Query,
    Response,
    Security,
    status,
)

from admin_api_lib.models.extra_models import TokenModel  # noqa: F401
from pydantic import Field, StrictBytes, StrictStr
from typing import Any, List, Optional, Tuple, Union
from typing_extensions import Annotated
from admin_api_lib.models.document_status import DocumentStatus
from admin_api_lib.models.key_value_pair import KeyValuePair


router = APIRouter()

ns_pkg = admin_api_lib.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.delete(
    "/delete_document/{identification}",
    responses={
        200: {"description": "Deleted"},
        500: {"description": "Internal server error"},
    },
    tags=["admin"],
    response_model_by_alias=True,
)
async def delete_document(
    identification: str = Path(..., description=""),
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
    if not BaseAdminApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseAdminApi.subclasses[0]().delete_document(identification)


@router.get(
    "/document_reference/{identification}",
    responses={
        200: {"model": UploadFile, "description": "Returns the pdf in binary form."},
        400: {"model": str, "description": "Bad request"},
        404: {"model": str, "description": "Document not found."},
        500: {"model": str, "description": "Internal server error"},
    },
    tags=["admin"],
    response_model_by_alias=True,
)
async def document_reference_id_get(
    identification: str = Path(..., description="Identifier of the pdf document."),
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
    if not BaseAdminApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseAdminApi.subclasses[0]().document_reference_id_get(identification)


@router.get(
    "/all_documents_status",
    responses={
        200: {"model": List[DocumentStatus], "description": "List of document links"},
        500: {"description": "Internal server error"},
    },
    tags=["admin"],
    response_model_by_alias=True,
)
async def get_all_documents_status() -> List[DocumentStatus]:
    """
    Asynchronously retrieves the status of all documents.

    Returns
    -------
    list[DocumentStatus]
        A list containing the status of all documents.
    """
    if not BaseAdminApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseAdminApi.subclasses[0]().get_all_documents_status()


@router.post(
    "/upload_source",
    responses={
        200: {"description": "ok"},
        400: {"description": "Bad request"},
        422: {"description": "If no text has been extracted from the file."},
        500: {"description": "Internal server error"},
    },
    tags=["admin"],
    response_model_by_alias=True,
)
async def upload_source(
    request: Request,
    type: Annotated[str, Form()],
    name: Annotated[str, Form()],
    file: Optional[UploadFile] = None,
    kwargs: Optional[Annotated[List[KeyValuePair], Form()]] = None,
) -> None:
    """Uploads user selected sources."""
    if not BaseAdminApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseAdminApi.subclasses[0]().upload_source(type, name, file, kwargs, request)
