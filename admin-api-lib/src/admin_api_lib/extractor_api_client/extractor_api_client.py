import requests
from admin_api_lib.extractor_api_client.models.information_piece import InformationPiece
from requests_toolbelt.multipart import MultipartEncoder


class ExtractorApiClient:
    def __init__(self, base_url):
        """
        Initialize the client with the base URL of the API.

        Args:
            base_url (str): The base URL of the API.
        """
        self.base_url = base_url

    def extract(self, type, name,  file, kwargs=None):
        """
        Send an extraction request to the API.

        Args:
            file (str): The path to the file to extract from.
            name (str): The name of the extraction request.
            type (str): The type of extraction to perform.
            kwargs (list): A list of key-value pairs to pass as additional arguments.

        Returns:
            list: A list of extracted information pieces.
        """
        with open(file, "rb") as openfile:
            url = self.base_url + "/extract"
            encoder = MultipartEncoder(
                fields={
                    "file": (file, openfile, "application/octet-stream"),
                    "name": name,
                    "type": type,
                }
            )
            if kwargs:
                for pair in kwargs:
                    encoder.add_field(pair["key"], pair["value"])
            response = requests.post(url, headers={"Content-Type": encoder.content_type}, data=encoder)
            if response.status_code == 200:
                response_json = response.json()
                return [InformationPiece.from_dict(x) for x in response_json]
            elif response.status_code == 422:
                raise ValueError("Invalid source")
            elif response.status_code == 500:
                raise Exception("Internal server error")
            else:
                raise Exception("Unknown error")
