from abc import ABC, abstractmethod
from typing import Optional

from pydantic import StrictStr
from fastapi import UploadFile

from admin_api_lib.models.key_value_pair import KeyValuePair


class SourceUploader(ABC):

    @abstractmethod
    async def upload_source(
        self,
        base_url: str,
        type: StrictStr,
        name: StrictStr,
        file: Optional[UploadFile],
        kwargs: Optional[list[KeyValuePair]],
    ) -> None: ...
