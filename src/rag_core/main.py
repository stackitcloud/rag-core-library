# coding: utf-8

"""
    RAG SIT x Stackit

    The perfect rag solution.

    The version of the OpenAPI document: 1.0.0
    Generated by OpenAPI Generator (https://openapi-generator.tech)

    Do not edit the class manually.
"""  # noqa: E501
from fastapi import FastAPI
from dependency_injector.containers import Container


from rag_core.apis.rag_api import router as RagApiRouter
from rag_core.dependency_container import DependencyContainer

app = FastAPI(
    title="RAG SIT x Stackit",
    description="The perfect rag solution.",
    version="1.0.0",
)

app.include_router(RagApiRouter)

container = DependencyContainer()
app.container = container


def register_dependency_container(new_container: Container):
    # preserve old wiring
    wiring_target = container.wiring_config.modules
    app.container.override(new_container)

    # rewire
    wiring_target = list(set(wiring_target + new_container.wiring_config.modules))
    app.container.wire(modules=wiring_target)
