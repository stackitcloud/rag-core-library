"""Module that contains settings regarding the vector db."""

from pydantic_settings import BaseSettings
from pydantic import Field

from langchain_qdrant import RetrievalMode


class VectorDatabaseSettings(BaseSettings):
    """
    Contains settings regarding the vector db.

    Attributes
    ----------
    collection_name : str
        The alias name of the collection.
    location : str
        The location of the vector database.
    collection_history_count : int
        Number of collections to keep in history (if updates are enabled, otherwise ignored).
        The number must be greater than or equal to 1.
    validate_collection_config : bool
        If true and collection does not exist, an error will be raised.
    retrieval_mode : RetrievalMode
        The mode used for retrieving documents (e.g., EMBEDDING, HYBRID).
    """

    class Config:
        """Config class for reading Fields from env."""

        env_prefix = "VECTOR_DB_"
        case_sensitive = False

    collection_name: str = Field()
    location: str = Field()
    collection_history_count: int = Field(default=1, ge=1)
    validate_collection_config: bool = Field(
        default=False
    )
    retrieval_mode: RetrievalMode = Field(default=RetrievalMode.HYBRID)
