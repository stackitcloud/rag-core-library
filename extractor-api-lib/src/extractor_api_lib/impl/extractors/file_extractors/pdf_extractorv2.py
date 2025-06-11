"""Module containing the PDFExtractor class."""

import logging
import re
import tempfile
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from enum import Enum

import cv2
import numpy as np
import pandas as pd
import pdfplumber
import easyocr
from pdf2image import convert_from_path
from pdfplumber.page import Page
from PIL import Image
import camelot
import tabula

from extractor_api_lib.impl.settings.pdf_extractor_settings import PDFExtractorSettings
from extractor_api_lib.impl.types.content_type import ContentType
from extractor_api_lib.impl.types.file_type import FileType
from extractor_api_lib.impl.utils.utils import hash_datetime
from extractor_api_lib.models.dataclasses.internal_information_piece import InternalInformationPiece
from extractor_api_lib.table_converter.dataframe_converter import DataframeConverter
from extractor_api_lib.file_services.file_service import FileService
from extractor_api_lib.extractors.information_file_extractor import InformationFileExtractor

logger = logging.getLogger(__name__)


class PageType(Enum):
    """Enum to classify page types."""
    TEXT_BASED = "text_based"
    SCANNED = "scanned"
    MIXED = "mixed"


class PDFExtractor(InformationFileExtractor):
    """Advanced PDFExtractor for extracting information from PDF files.

    This extractor intelligently determines whether PDF pages are text-based or scanned,
    and applies the appropriate extraction method. For mixed content pages (text + images),
    it extracts text content and images separately without performing OCR, linking them
    through related IDs. It supports multiple table extraction methods and efficient
    OCR for scanned documents.

    Attributes
    ----------
    TITLE_PATTERN : re.Pattern
        Regular expression pattern to identify titles in the text.
    TITLE_PATTERN_MULTILINE : re.Pattern
        Regular expression pattern to identify titles with multiline support.
    TEXT_THRESHOLD : float
        Threshold for determining if a page has extractable text (default: 50 characters).
    """

    TITLE_PATTERN = re.compile(r"(^|\n)(\d+\.[\.\d]*[\t ][a-zA-Z0-9 äöüÄÖÜß\-]+)")
    TITLE_PATTERN_MULTILINE = re.compile(r"(^|\n)(\d+\.[\.\d]*[\t ][a-zA-Z0-9 äöüÄÖÜß\-]+)", re.MULTILINE)
    TEXT_THRESHOLD = 50  # Minimum characters to consider page as text-based

    def __init__(
        self,
        file_service: FileService,
        pdf_extractor_settings: PDFExtractorSettings,
        dataframe_converter: DataframeConverter,
    ):
        """Initialize the PDFExtractor.

        Parameters
        ----------
        file_service : FileService
            Handler for downloading and uploading files.
        pdf_extractor_settings : PDFExtractorSettings
            Settings for the PDF extractor.
        dataframe_converter: DataframeConverter
            Converter for dataframe tables to a search and saveable format.
        """
        super().__init__(file_service=file_service)
        self._dataframe_converter = dataframe_converter
        self._settings = pdf_extractor_settings

        # Initialize EasyOCR reader (more efficient than Tesseract)
        # Support multiple languages - can be configured via settings
        self._ocr_reader = easyocr.Reader(['en', 'de'], gpu=False)  # CPU-only for better compatibility

    @property
    def compatible_file_types(self) -> list[FileType]:
        """
        Returns a list of compatible file types for the PDF extractor.

        Returns
        -------
        list[FileType]
            A list containing the FileType.PDF indicating that this extractor is compatible with PDF files.
        """
        return [FileType.PDF]

    @staticmethod
    def _create_information_piece(
        document_name: str,
        page: int,
        title: str,
        content: str,
        content_type: ContentType,
        information_id: str,
        additional_meta: Optional[dict] = None,
    ) -> InternalInformationPiece:
        metadata = {
            "document": document_name,
            "page": page,
            "title": title,
            "id": information_id,
            "related": [],
        }
        if additional_meta:
            metadata = metadata | additional_meta
        return InternalInformationPiece(
            type=content_type,
            metadata=metadata,
            page_content=content,
        )

    async def aextract_content(self, file_path: Path, name: str) -> list[InternalInformationPiece]:
        """Extract content from given PDF file.

        This method intelligently determines whether each page is text-based or scanned
        and applies the appropriate extraction method.

        Parameters
        ----------
        file_path : Path
            Path to the PDF file.
        name : str
            Name of the document.

        Returns
        -------
        list[InternalInformationPiece]
            The extracted information pieces.
        """
        logger.info(f"Starting extraction for PDF: {name}")
        pdf_elements = []
        current_title = ""

        with pdfplumber.open(file_path) as pdf:
            for page_idx, page in enumerate(pdf.pages, 1):
                logger.debug(f"Processing page {page_idx}/{len(pdf.pages)}")

                # Determine page type (text-based, scanned, or mixed)
                page_type = self._classify_page_type(page)
                logger.debug(f"Page {page_idx} classified as: {page_type.value}")

                # Extract content based on page type
                (new_pdf_elements, current_title) = await self._extract_content_from_page(
                    page_index=page_idx,
                    page=page,
                    page_type=page_type,
                    title=current_title,
                    document_name=name,
                    file_path=file_path,
                )
                pdf_elements += new_pdf_elements

        logger.info(f"Extraction completed. Found {len(pdf_elements)} information pieces.")
        return pdf_elements

    def _classify_page_type(self, page: Page) -> PageType:
        """Classify whether a page is text-based, scanned, or mixed.

        Parameters
        ----------
        page : Page
            The pdfplumber page object.

        Returns
        -------
        PageType
            The classification of the page type.
        """
        # Try to extract text using pdfplumber
        extractable_text = page.extract_text() or ""

        # Clean and count meaningful text
        meaningful_text = re.sub(r'\s+', ' ', extractable_text.strip())

        # Check for images in the page
        has_images = len(page.images) > 0

        if len(meaningful_text) >= self.TEXT_THRESHOLD:
            if has_images:
                return PageType.MIXED
            else:
                return PageType.TEXT_BASED
        else:
            return PageType.SCANNED

    async def _extract_content_from_page(
        self,
        page_index: int,
        page: Page,
        page_type: PageType,
        title: str,
        document_name: str,
        file_path: Path,
    ) -> Tuple[list[InternalInformationPiece], str]:
        """Extract content from a single page based on its type.

        Parameters
        ----------
        page_index : int
            The page number (1-indexed).
        page : Page
            The pdfplumber page object.
        page_type : PageType
            The classification of the page.
        title : str
            Current title context.
        document_name : str
            Name of the document.
        file_path : Path
            Path to the PDF file.

        Returns
        -------
        Tuple[list[InternalInformationPiece], str]
            Tuple of (extracted elements, updated title).
        """
        pdf_elements = []

        # Extract text based on page type
        if page_type == PageType.TEXT_BASED:
            content = self._extract_text_from_text_page(page)
            table_elements = self._extract_tables_from_text_page(page, page_index, document_name)
        elif page_type == PageType.SCANNED:
            content = await self._extract_text_from_scanned_page(page, page_index, file_path)
            table_elements = self._extract_tables_from_scanned_page(page, page_index, document_name, file_path)
        else:  # MIXED
            # For mixed pages with images, only use text-based extraction (no OCR)
            # Images will be extracted separately and linked to text content
            content = self._extract_text_from_text_page(page)
            table_elements = self._extract_tables_from_text_page(page, page_index, document_name)

        # Process extracted text and collect text element IDs for linking
        text_element_ids = []
        if content and content.strip():
            text_elements = self._process_text_content(content, title, page_index, document_name)
            pdf_elements.extend(text_elements)
            # Collect IDs for linking with images
            text_element_ids = [element.metadata["id"] for element in text_elements]

        # Add table elements and collect their IDs
        table_element_ids = []
        if table_elements:
            pdf_elements.extend(table_elements)
            table_element_ids = [element.metadata["id"] for element in table_elements]

        # Extract images if present and link them to text/table elements
        image_elements = self._extract_images(page, page_index, document_name)
        if image_elements:
            # Link images to text and table elements on the same page
            related_ids = text_element_ids + table_element_ids
            for image_element in image_elements:
                image_element.metadata["related"] = related_ids
                # Also add image IDs to text and table elements
                for element in pdf_elements:
                    if element.metadata["page"] == page_index and element.metadata["id"] in related_ids:
                        if "related" not in element.metadata:
                            element.metadata["related"] = []
                        element.metadata["related"].append(image_element.metadata["id"])

            pdf_elements.extend(image_elements)

        # Update title if found in content
        updated_title = self._extract_title_from_content(content) or title

        return pdf_elements, updated_title

    def _extract_text_from_text_page(self, page: Page) -> str:
        """Extract text from a text-based page using pdfplumber.

        Parameters
        ----------
        page : Page
            The pdfplumber page object.

        Returns
        -------
        str
            Extracted text content.
        """
        try:
            return page.extract_text() or ""
        except Exception as e:
            logger.warning(f"Failed to extract text with pdfplumber: {e}")
            return ""

    async def _extract_text_from_scanned_page(self, page: Page, page_index: int, file_path: Path) -> str:
        """Extract text from a scanned page using OCR.

        Parameters
        ----------
        page : Page
            The pdfplumber page object.
        page_index : int
            The page number.
        file_path : Path
            Path to the PDF file.

        Returns
        -------
        str
            Extracted text content using OCR.
        """
        try:
            # Convert specific page to image
            images = convert_from_path(file_path, first_page=page_index, last_page=page_index)
            if not images:
                return ""

            # Convert PIL image to numpy array for EasyOCR
            image = np.array(images[0])

            # Use EasyOCR to extract text
            ocr_results = self._ocr_reader.readtext(image)

            # Combine OCR results into text
            extracted_text = ' '.join([result[1] for result in ocr_results if result[2] > 0.5])  # confidence > 0.5

            return extracted_text

        except Exception as e:
            logger.warning(f"Failed to extract text with OCR for page {page_index}: {e}")
            return ""

    def _extract_tables_from_text_page(self, page: Page, page_index: int, document_name: str) -> list[InternalInformationPiece]:
        """Extract tables from text-based page using pdfplumber.

        Parameters
        ----------
        page : Page
            The pdfplumber page object.
        page_index : int
            The page number.
        document_name : str
            Name of the document.

        Returns
        -------
        list[InternalInformationPiece]
            List of extracted table information pieces.
        """
        table_elements = []

        try:
            # Use pdfplumber for table extraction
            tables = page.find_tables()

            for i, table in enumerate(tables):
                try:
                    # Extract table data with error handling
                    table_data = table.extract()
                    if not table_data or all(not row or all(not cell for cell in row) for row in table_data):
                        continue

                    # Convert to DataFrame
                    table_df = pd.DataFrame(table_data[1:], columns=table_data[0] if table_data[0] else None)

                    # Convert using dataframe converter
                    converted_table = self._dataframe_converter.convert(table_df)

                    if converted_table and converted_table.strip():
                        table_elements.append(
                            self._create_information_piece(
                                document_name,
                                page_index,
                                f"Table {i+1}",
                                converted_table,
                                ContentType.TABLE,
                                information_id=hash_datetime(),
                                additional_meta={"table_method": "pdfplumber", "table_index": i}
                            )
                        )

                except Exception as e:
                    logger.warning(f"Failed to extract table {i+1} from page {page_index}: {e}")
                    continue

        except Exception as e:
            logger.warning(f"Failed to find tables on page {page_index}: {e}")

        return table_elements

    def _extract_tables_from_scanned_page(self, page: Page, page_index: int, document_name: str, file_path: Path) -> list[InternalInformationPiece]:
        """Extract tables from scanned page using multiple methods.

        Parameters
        ----------
        page : Page
            The pdfplumber page object.
        page_index : int
            The page number.
        document_name : str
            Name of the document.
        file_path : Path
            Path to the PDF file.

        Returns
        -------
        list[InternalInformationPiece]
            List of extracted table information pieces.
        """
        table_elements = []

        # Method 1: Try Camelot (good for scanned tables)
        try:
            camelot_tables = camelot.read_pdf(str(file_path), pages=str(page_index), flavor='stream')

            for i, table in enumerate(camelot_tables):
                if table.accuracy > 50:  # Only use tables with good accuracy
                    try:
                        converted_table = self._dataframe_converter.convert(table.df)
                        if converted_table and converted_table.strip():
                            table_elements.append(
                                self._create_information_piece(
                                    document_name,
                                    page_index,
                                    f"Table {i+1}",
                                    converted_table,
                                    ContentType.TABLE,
                                    information_id=hash_datetime(),
                                    additional_meta={"table_method": "camelot", "accuracy": table.accuracy, "table_index": i}
                                )
                            )
                    except Exception as e:
                        logger.warning(f"Failed to convert Camelot table {i+1}: {e}")

        except Exception as e:
            logger.debug(f"Camelot table extraction failed for page {page_index}: {e}")

        # Method 2: Try Tabula as fallback
        if not table_elements:
            try:
                tabula_tables = tabula.read_pdf(str(file_path), pages=page_index, multiple_tables=True)

                for i, table_df in enumerate(tabula_tables):
                    if not table_df.empty:
                        try:
                            converted_table = self._dataframe_converter.convert(table_df)
                            if converted_table and converted_table.strip():
                                table_elements.append(
                                    self._create_information_piece(
                                        document_name,
                                        page_index,
                                        f"Table {i+1}",
                                        converted_table,
                                        ContentType.TABLE,
                                        information_id=hash_datetime(),
                                        additional_meta={"table_method": "tabula", "table_index": i}
                                    )
                                )
                        except Exception as e:
                            logger.warning(f"Failed to convert Tabula table {i+1}: {e}")

            except Exception as e:
                logger.debug(f"Tabula table extraction failed for page {page_index}: {e}")

        return table_elements

    def _extract_images(self, page: Page, page_index: int, document_name: str) -> list[InternalInformationPiece]:
        """Extract image information from page.

        Parameters
        ----------
        page : Page
            The pdfplumber page object.
        page_index : int
            The page number.
        document_name : str
            Name of the document.

        Returns
        -------
        list[InternalInformationPiece]
            List of image information pieces.
        """
        image_elements = []

        try:
            images = page.images

            for i, img in enumerate(images):
                # Create image metadata
                image_info = {
                    "x0": img.get("x0", 0),
                    "y0": img.get("y0", 0),
                    "x1": img.get("x1", 0),
                    "y1": img.get("y1", 0),
                    "width": img.get("width", 0),
                    "height": img.get("height", 0),
                    "image_index": i,
                    "extraction_method": "pdfplumber"
                }

                # Create enhanced descriptive content for the image
                content = (
                    f"Image {i+1} on page {page_index}\n"
                    f"Position: ({img.get('x0', 0):.1f}, {img.get('y0', 0):.1f}) to "
                    f"({img.get('x1', 0):.1f}, {img.get('y1', 0):.1f})\n"
                    f"Dimensions: {img.get('width', 0):.1f} x {img.get('height', 0):.1f} points\n"
                    f"This image is located alongside text content on the page and is "
                    f"linked to related text and table elements through metadata."
                )

                image_elements.append(
                    self._create_information_piece(
                        document_name,
                        page_index,
                        f"Image {i+1}",
                        content,
                        ContentType.IMAGE,
                        information_id=hash_datetime(),
                        additional_meta=image_info
                    )
                )

        except Exception as e:
            logger.warning(f"Failed to extract images from page {page_index}: {e}")

        return image_elements

    def _process_text_content(self, content: str, title: str, page_index: int, document_name: str) -> list[InternalInformationPiece]:
        """Process text content and split by titles.

        Parameters
        ----------
        content : str
            Raw text content.
        title : str
            Current title context.
        page_index : int
            The page number.
        document_name : str
            Name of the document.

        Returns
        -------
        list[InternalInformationPiece]
            List of processed text information pieces.
        """
        text_elements = []

        if not content or not content.strip():
            return text_elements

        # Split content by title patterns
        content_array = re.split(self.TITLE_PATTERN_MULTILINE, content)
        content_array = [x.strip() for x in content_array if x and x.strip()]

        current_title = title

        for content_item in content_array:
            is_title = re.match(self.TITLE_PATTERN, content_item)
            if is_title:
                current_title = content_item.strip()
            else:
                # Create text piece with current title context
                full_content = f"{current_title}\n{content_item}" if current_title else content_item

                text_elements.append(
                    self._create_information_piece(
                        document_name,
                        page_index,
                        current_title,
                        full_content,
                        ContentType.TEXT,
                        information_id=hash_datetime(),
                    )
                )

        return text_elements

    def _merge_text_content(self, text_content: str, ocr_content: str) -> str:
        """Merge text from different extraction methods.

        Parameters
        ----------
        text_content : str
            Text extracted from text-based methods.
        ocr_content : str
            Text extracted from OCR.

        Returns
        -------
        str
            Merged text content.
        """
        # If text-based extraction yielded substantial content, prefer it
        if len(text_content.strip()) >= self.TEXT_THRESHOLD:
            return text_content

        # Otherwise, use OCR content or combine if both have content
        if text_content.strip() and ocr_content.strip():
            return f"{text_content}\n\n--- OCR Content ---\n{ocr_content}"

        return ocr_content or text_content

    def _merge_table_elements(self, text_tables: list[InternalInformationPiece], scanned_tables: list[InternalInformationPiece]) -> list[InternalInformationPiece]:
        """Merge table elements from different extraction methods.

        Parameters
        ----------
        text_tables : list[InternalInformationPiece]
            Tables extracted from text-based methods.
        scanned_tables : list[InternalInformationPiece]
            Tables extracted from scanned/OCR methods.

        Returns
        -------
        list[InternalInformationPiece]
            Combined list of unique table elements.
        """
        # Prefer text-based tables if available
        if text_tables:
            return text_tables

        return scanned_tables

    def _extract_title_from_content(self, content: str) -> Optional[str]:
        """Extract title from content if present.

        Parameters
        ----------
        content : str
            Text content to search for titles.

        Returns
        -------
        Optional[str]
            Extracted title if found, None otherwise.
        """
        if not content:
            return None

        # Look for title patterns at the beginning of content
        lines = content.split('\n')
        for line in lines[:3]:  # Check first 3 lines
            line = line.strip()
            if re.match(self.TITLE_PATTERN, line):
                return line

        return None
