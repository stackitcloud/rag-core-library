# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from extractor_api_lib.apis.extractor_api_base import BaseExtractorApi
import openapi_server.impl

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

from extractor_api_lib.models.extra_models import TokenModel  # noqa: F401
from pydantic import StrictBytes, StrictStr
from fastapi import Request, Response, UploadFile
from typing import Any, List, Optional, Tuple, Union
from extractor_api_lib.models.information_piece import InformationPiece
from extractor_api_lib.models.key_value_pair import KeyValuePair


router = APIRouter()

ns_pkg = openapi_server.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.post(
    "/extract",
    responses={
        200: {"model": List[InformationPiece], "description": "List of extracted information."},
        422: {"description": "Body is not a valid source."},
        500: {"description": "Something somewhere went terribly wrong."},
    },
    tags=["extractor"],
    response_model_by_alias=True,
)
async def extract(
    type: StrictStr = Form(None, description=""),
    name: StrictStr = Form(None, description=""),
    file: Optional[UploadFile] = Form(None, description=""),
    kwargs: Optional[List[KeyValuePair]] = Form(None, description=""),
) -> List[InformationPiece]:
    if not BaseExtractorApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseExtractorApi.subclasses[0]().extract(type, name, file, kwargs)
