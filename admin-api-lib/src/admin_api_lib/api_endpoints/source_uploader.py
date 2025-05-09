from dataclasses import Field
from typing_extensions import Annotated
from abc import ABC, abstractmethod

from admin_api_lib.models.upload_source import UploadSource


class SourceUploader(ABC):

    @abstractmethod
    async def upload_source(
        self,
        upload_source: Annotated[UploadSource, Field(description="The source to upload.")],
    ) -> None: ...
