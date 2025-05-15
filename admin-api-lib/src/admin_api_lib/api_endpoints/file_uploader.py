from abc import ABC, abstractmethod

from fastapi import UploadFile



class FileUploader(ABC):

    @abstractmethod
    async def upload_file(
        self,
        base_url: str,
        file: UploadFile,        
    ) -> None: ...
