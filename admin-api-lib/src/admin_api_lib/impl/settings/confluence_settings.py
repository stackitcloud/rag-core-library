"""Contains settings regarding the confluence."""

from typing import Optional
from admin_api_lib.impl.utils.comma_separated_bool_list import CommaSeparatedBoolList
from admin_api_lib.impl.utils.comma_separated_str_list import CommaSeparatedStrList
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings
import logging

logger = logging.getLogger(__name__)


class ConfluenceSettings(BaseSettings):
    """
    Contains configuration settings for the Confluence integration.

    Parameters
    ----------
    url : CommaSeparatedStrList, optional
        List of Confluence URLs.
    token : CommaSeparatedStrList, optional
        List of authentication tokens.
    space_key : CommaSeparatedStrList, optional
        List of Confluence space keys.
    document_name : CommaSeparatedStrList, optional
        List of document names.
    verify_ssl : CommaSeparatedBoolList, optional
        List of booleans indicating whether SSL verification is enabled.
    include_attachments : CommaSeparatedBoolList, optional
        Indicates whether to include attachments in the integration.
    keep_markdown_format : CommaSeparatedBoolList, optional
        Determines if markdown formatting is maintained.
    keep_newlines : CommaSeparatedBoolList, optional
        Indicates whether newlines are preserved.
    max_pages : CommaSeparatedStrList, optional
        List of maximum number of pages to retrieve per Confluence space.
    """

    class Config:
        """Config class for reading Fields from env."""

        env_prefix = "CONFLUENCE_"
        case_sensitive = False

    url: Optional[CommaSeparatedStrList] = Field(default_factory=CommaSeparatedStrList)
    token: Optional[CommaSeparatedStrList] = Field(default_factory=CommaSeparatedStrList)
    space_key: Optional[CommaSeparatedStrList] = Field(default_factory=CommaSeparatedStrList)
    document_name: Optional[CommaSeparatedStrList] = Field(default_factory=CommaSeparatedStrList)
    verify_ssl: Optional[CommaSeparatedBoolList] = Field(default_factory=CommaSeparatedBoolList)
    include_attachments: Optional[CommaSeparatedBoolList] = Field(default_factory=CommaSeparatedBoolList)
    keep_markdown_format: Optional[CommaSeparatedBoolList] = Field(default_factory=CommaSeparatedBoolList)
    keep_newlines: Optional[CommaSeparatedBoolList] = Field(default_factory=CommaSeparatedBoolList)
    max_pages: Optional[CommaSeparatedStrList] = Field(default_factory=CommaSeparatedStrList)


    @model_validator(mode="after")
    def check_lists_length_consistency(cls, values):
        """
        Validate that all list-valued settings have the same length.

        If not, the list is adjusted accordingly.

        Parameters
        ----------
        values : dict
            Dictionary of configuration settings.

        Returns
        -------
        dict
            The validated values dictionary with consistent list lengths.

        Raises
        ------
        ValueError
            If any non-optional list has a different length compared to others.
        """
        # Define the keys to check
        keys = [
            "url",
            "token",
            "space_key",
            "document_name",
            "verify_ssl",
            "include_attachments",
            "keep_markdown_format",
            "keep_newlines",
            "max_pages",
        ]

        lengths = {}
        for key in keys:
            value = getattr(values, key, None)
            if value is not None:
                lengths[key] = len(value)
        # If there is more than one list with values, ensure they have the same length
        optional_keys = ["document_name", "verify_ssl", "include_attachments", "keep_markdown_format", "keep_newlines", "max_pages"]
        if lengths:
            # Use the first encountered length as reference
            ref_length = next(iter(lengths.values()))
            for key, length in lengths.items():
                if length != ref_length and key not in optional_keys:
                    raise ValueError(
                        f"Confluence Settings length mismatch: Expected all lists to have {ref_length} elements, "
                        f"but '{key}' has {length} elements. {lengths}"
                    )

        urls = getattr(values, "url", None)
        if urls and len(urls) > 0:
            n = len(urls)
            # Existing code for other parameters...

            # Add handling for max_pages
            try:
                max_pages = getattr(values, "max_pages", None)
                if not max_pages or len(max_pages) == 0:
                    values.max_pages = CommaSeparatedStrList(["0"] * n)  # 0 means no limit
                elif len(max_pages) != n:
                    raise ValueError("max_pages list length mismatch")
            except ValueError as e:
                logger.error(f"Error setting max_pages: {e}")
                logger.warning("Setting max_pages to default values")
                max_pages = getattr(values, "max_pages", [])
                values.max_pages = CommaSeparatedStrList(max_pages + ["0"] * (n - len(max_pages)))

            # Rest of the existing parameter handlers...
            try:
                document_name = getattr(values, "document_name", None)
                if not document_name or len(document_name) == 0:
                    values.document_name = CommaSeparatedStrList([""] * n)
                elif len(document_name) != n:
                    raise ValueError("document_name list length mismatch")
            except ValueError as e:
                logger.error(f"Error setting document_name: {e}")
                logger.warning("Setting document_name to default values")
                document_name = getattr(values, "document_name", [])
                values.document_name = CommaSeparatedStrList(document_name + [""] * (n - len(document_name)))

            try:
                verify_ssl = getattr(values, "verify_ssl", None)
                if not verify_ssl or len(verify_ssl) == 0:
                    values.verify_ssl = CommaSeparatedBoolList([True] * n)
                elif len(verify_ssl) != n:
                    raise ValueError("verify_ssl list length mismatch")
            except ValueError as e:
                logger.error(f"Error setting verify_ssl: {e}")
                logger.warning("Setting verify_ssl to default values")
                verify_ssl = getattr(values, "verify_ssl", [])
                values.verify_ssl = CommaSeparatedBoolList(verify_ssl + [True] * (n - len(verify_ssl)))

            try:
                include_attachments = getattr(values, "include_attachments", None)
                if not include_attachments or len(include_attachments) == 0:
                    values.include_attachments = CommaSeparatedBoolList([False] * n)
                elif len(include_attachments) != n:
                    raise ValueError("include_attachments list length mismatch")
            except ValueError as e:
                logger.error(f"Error setting include_attachments: {e}")
                logger.warning("Setting include_attachments to default values")
                include_attachments = getattr(values, "include_attachments", [])
                values.include_attachments = CommaSeparatedBoolList(
                    include_attachments + [False] * (n - len(include_attachments))
                )

            try:
                keep_markdown_format = getattr(values, "keep_markdown_format", None)
                if not keep_markdown_format or len(keep_markdown_format) == 0:
                    values.keep_markdown_format = CommaSeparatedBoolList([True] * n)
                elif len(keep_markdown_format) != n:
                    raise ValueError("keep_markdown_format list length mismatch")
            except ValueError as e:
                logger.error(f"Error setting keep_markdown_format: {e}")
                logger.warning("Setting keep_markdown_format to default values")
                keep_markdown_format = getattr(values, "keep_markdown_format", [])
                values.keep_markdown_format = CommaSeparatedBoolList(
                    keep_markdown_format + [True] * (n - len(keep_markdown_format))
                )

            try:
                keep_newlines = getattr(values, "keep_newlines", None)
                if not keep_newlines or len(keep_newlines) == 0:
                    values.keep_newlines = CommaSeparatedBoolList([True] * n)
                elif len(keep_newlines) != n:
                    raise ValueError("keep_newlines list length mismatch")
            except ValueError as e:
                logger.error(f"Error setting keep_newlines: {e}")
                logger.warning("Setting keep_newlines to default values")
                keep_newlines = getattr(values, "keep_newlines", [])
                values.keep_newlines = CommaSeparatedBoolList(keep_newlines + [True] * (n - len(keep_newlines)))

        return values
