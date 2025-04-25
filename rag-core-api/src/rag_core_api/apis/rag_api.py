"""Module containing the RAG API endpoints."""

# coding: utf-8
# flake8: noqa: D105

import importlib
import logging
import pkgutil
from asyncio import FIRST_COMPLETED, CancelledError, create_task, sleep, wait
from contextlib import suppress
from typing import Any, Awaitable, List  # noqa: F401

from fastapi import (  # noqa: F401
    APIRouter,
    BackgroundTasks,
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

import rag_core_api.impl
from rag_core_api.apis.rag_api_base import BaseRagApi
from rag_core_api.models.chat_request import ChatRequest
from rag_core_api.models.chat_response import ChatResponse
from rag_core_api.models.delete_request import DeleteRequest
from rag_core_api.models.upload_request import UploadRequest

logger = logging.getLogger(__name__)

router = APIRouter()

ns_pkg = rag_core_api.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


async def _disconnected(request: Request) -> None:
    while True:
        try:
            if await request.is_disconnected():
                break
            await sleep(1.0)
        except CancelledError:
            break


@router.post(
    "/chat/{session_id}",
    responses={
        200: {"model": ChatResponse, "description": "OK."},
        500: {"description": "Internal Server Error!"},
    },
    tags=["rag"],
    response_model_by_alias=True,
)
async def chat(
    request: Request,
    session_id: str = Path(..., description=""),
    chat_request: ChatRequest = Body(None, description="Chat with RAG."),
) -> ChatResponse | None:
    """
    Asynchronously handles the chat endpoint for the RAG API.

    Parameters
    ----------
    request : Request
        The request object.
    session_id : str
        The session ID for the chat.
    chat_request : ChatRequest, optional
        The chat request payload

    Returns
    -------
    ChatResponse or None
        The chat response if the chat task completes successfully, otherwise None.

    Raises
    ------
    CancelledError
        If the task is cancelled.

    Notes
    -----
    This function creates two asynchronous tasks: one for handling disconnection and one for processing the chat
    request. It waits for either task to complete first and cancels the remaining tasks.
    """
    disconnect_task = create_task(_disconnected(request))
    chat_task = create_task(BaseRagApi.subclasses[0]().chat(session_id, chat_request))
    done, pending = await wait(
        [disconnect_task, chat_task],
        return_when=FIRST_COMPLETED,
    )

    # cancel all remaining tasks
    for task in pending:
        task.cancel()
        with suppress(CancelledError):
            await task
    if chat_task in done:
        return chat_task.result()
    logger.info("Request got cancelled!")
    return None


@router.post(
    "/collection/duplicate",
    responses={
        201: {"description": "Duplication created successfully."},
        404: {"description": "No production collection found."},
        500: {"description": "Internal server error."},
    },
    tags=["rag"],
    summary="Duplicates a vector database collection.",
    response_model_by_alias=True,
)
async def duplicate_collection() -> None:
    """Duplicates a vector database collection. It uses the production collection for duplication."""
    return await BaseRagApi.subclasses[0]().duplicate_collection()


@router.post(
    "/evaluate",
    responses={
        201: {"description": "Accepted."},
        500: {"description": "Internal Server Error."},
    },
    tags=["rag"],
    response_model_by_alias=True,
)
async def evaluate() -> None:
    """
    Asynchronously evaluate the RAG.

    Returns
    -------
    None
    """
    return await BaseRagApi.subclasses[0]().evaluate()


@router.post(
    "/information_pieces/remove",
    responses={
        202: {"description": "Accepted."},
        404: {"description": "Ressource not Found"},
        422: {"description": "ID or metadata missing."},
        500: {"description": "Internal Server Error."},
    },
    tags=["rag"],
    summary="remove information piece",
    response_model_by_alias=True,
)
async def remove_information_piece(
    delete_request: DeleteRequest = Body(None, description=""),
) -> None:
    """
    Asynchronously removes information pieces.

    This endpoint removes information pieces based on the provided delete request.

    Parameters
    ----------
    delete_request : DeleteRequest
        The request body containing the details for the information piece to be removed.

    Returns
    -------
    None
    """
    return await BaseRagApi.subclasses[0]().remove_information_piece(delete_request)


@router.post(
    "/collection/switch",
    responses={
        200: {"description": "Collection alias has been successfully switched."},
        404: {"description": "Source or target collection not found."},
        500: {"description": "Internal server error."},
    },
    tags=["rag"],
    summary="Switch production vectordatabase.",
    response_model_by_alias=True,
)
async def switch_collection() -> None:
    """Remove the production alias from source collection and add that alias to target collection"""
    return await BaseRagApi.subclasses[0]().switch_collection()


@router.post(
    "/information_pieces/upload",
    responses={
        201: {"description": "The file was successful uploaded."},
        422: {"model": str, "description": "Wrong json format."},
        500: {"model": str, "description": "Internal Server Error."},
    },
    tags=["rag"],
    summary="Upload information pieces for vectordatabase",
    response_model_by_alias=True,
)
async def upload_information_piece(
    upload_request: UploadRequest = Body(None, description=""),
) -> None:
    """
    Asynchronously uploads information pieces to the vector database.

    Parameters
    ----------
    upload_request : UploadRequest
        The request payload containing the information pieces to be uploaded (default None).

    Returns
    -------
    None
    """
    return await BaseRagApi.subclasses[0]().upload_information_piece(upload_request)
