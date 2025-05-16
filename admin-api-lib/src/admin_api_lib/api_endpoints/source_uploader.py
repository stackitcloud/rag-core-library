from abc import ABC, abstractmethod

from pydantic import StrictStr

from admin_api_lib.models.key_value_pair import KeyValuePair


class SourceUploader(ABC):

    @abstractmethod
    async def upload_source(
        self,
        base_url: str,
        source_type: StrictStr,
        name: StrictStr,
        kwargs: list[KeyValuePair],
    ) -> None: ...
