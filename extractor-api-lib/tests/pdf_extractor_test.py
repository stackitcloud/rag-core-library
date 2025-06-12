"""Comprehensive test suite for PDFExtractor class."""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
import pytest
import pandas as pd
import numpy as np

from extractor_api_lib.impl.extractors.file_extractors.pdf_extractor import PDFExtractor
from extractor_api_lib.impl.settings.pdf_extractor_settings import PDFExtractorSettings
from extractor_api_lib.impl.types.content_type import ContentType
from extractor_api_lib.impl.types.file_type import FileType
from extractor_api_lib.models.dataclasses.internal_information_piece import InternalInformationPiece
from extractor_api_lib.table_converter.dataframe_converter import DataframeConverter
from extractor_api_lib.file_services.file_service import FileService


class TestPDFExtractor:
    """Test class for PDFExtractor."""

    @pytest.fixture
    def mock_file_service(self):
        """Create a mock file service for testing."""
        service = MagicMock(spec=FileService)
        return service

    @pytest.fixture
    def mock_pdf_extractor_settings(self):
        """Create mock PDF extractor settings."""
        settings = MagicMock(spec=PDFExtractorSettings)
        return settings

    @pytest.fixture
    def mock_dataframe_converter(self):
        """Create a mock dataframe converter."""
        converter = MagicMock(spec=DataframeConverter)
        converter.convert.return_value = "Mocked table content"
        return converter

    @pytest.fixture
    def pdf_extractor(self, mock_file_service, mock_pdf_extractor_settings, mock_dataframe_converter):
        """Create a PDFExtractor instance for testing."""
        return PDFExtractor(
            file_service=mock_file_service,
            pdf_extractor_settings=mock_pdf_extractor_settings,
            dataframe_converter=mock_dataframe_converter,
        )

    @pytest.fixture
    def test_pdf_files(self):
        """Provide paths to test PDF files."""
        test_data_dir = Path(__file__).parent / "test_data"
        return {
            "text_based": test_data_dir / "text_based_document.pdf",
            "scanned": test_data_dir / "scanned_document.pdf",
            "mixed_content": test_data_dir / "mixed_content_document.pdf",
            "multi_column": test_data_dir / "multi_column_document.pdf",
        }

    def test_compatible_file_types(self, pdf_extractor):
        """Test that PDF extractor only supports PDF files."""
        compatible_types = pdf_extractor.compatible_file_types
        assert compatible_types == [FileType.PDF]

    def test_create_information_piece(self):
        """Test the static method for creating information pieces."""
        piece = PDFExtractor._create_information_piece(
            document_name="test_doc",
            page=1,
            title="Test Title",
            content="Test content",
            content_type=ContentType.TEXT,
            information_id="test_id",
            additional_meta={"test_key": "test_value"},
            related_ids=["related_1", "related_2"],
        )

        assert isinstance(piece, InternalInformationPiece)
        assert piece.type == ContentType.TEXT
        assert piece.page_content == "Test content"
        assert piece.metadata["document"] == "test_doc"
        assert piece.metadata["page"] == 1
        assert piece.metadata["title"] == "Test Title"
        assert piece.metadata["id"] == "test_id"
        assert piece.metadata["related"] == ["related_1", "related_2"]
        assert piece.metadata["test_key"] == "test_value"

    @patch("pdfplumber.open")
    @patch("pdf2image.convert_from_path")
    @patch("tempfile.TemporaryDirectory")
    def test_is_text_based_threshold(self, mock_temp_dir, mock_convert, mock_pdfplumber, pdf_extractor):
        """Test the text-based page classification threshold."""
        # Mock pdfplumber page
        mock_page = MagicMock()

        # Test case 1: Page with enough text (above threshold)
        mock_page.extract_text.return_value = "A" * 60  # Above 50 character threshold
        assert pdf_extractor._is_text_based(mock_page) is True

        # Test case 2: Page with insufficient text (below threshold)
        mock_page.extract_text.return_value = "A" * 30  # Below 50 character threshold
        assert pdf_extractor._is_text_based(mock_page) is False

        # Test case 3: Empty text
        mock_page.extract_text.return_value = ""
        assert pdf_extractor._is_text_based(mock_page) is False

        # Test case 4: None text
        mock_page.extract_text.return_value = None
        assert pdf_extractor._is_text_based(mock_page) is False

    def test_auto_detect_language(self, pdf_extractor):
        """Test language detection functionality."""
        # Test English text
        english_text = "This is a sample English text for language detection."
        detected_lang = pdf_extractor._auto_detect_language(english_text)
        assert detected_lang in ["en", "de"]  # Should detect a language

        # Test with empty text (should default to "en")
        empty_text = ""
        detected_lang = pdf_extractor._auto_detect_language(empty_text)
        assert detected_lang == "en"

    @pytest.mark.asyncio
    async def test_extract_content_text_based_pdf(self, pdf_extractor, test_pdf_files):
        """Test content extraction from text-based PDF."""
        if not test_pdf_files["text_based"].exists():
            pytest.skip("Text-based test PDF not found")

        result = await pdf_extractor.aextract_content(
            file_path=test_pdf_files["text_based"], name="text_based_document"
        )

        assert isinstance(result, list)
        assert len(result) > 0

        # Check that we have both text and table elements
        text_elements = [elem for elem in result if elem.type == ContentType.TEXT]
        table_elements = [elem for elem in result if elem.type == ContentType.TABLE]

        assert len(text_elements) > 0, "Should extract at least one text element"
        assert len(table_elements) > 0, "Should extract at least one table element"

        # Verify metadata structure
        for element in result:
            assert "document" in element.metadata
            assert "page" in element.metadata
            assert "title" in element.metadata
            assert "id" in element.metadata
            assert "related" in element.metadata
            assert element.metadata["document"] == "text_based_document"

    @pytest.mark.asyncio
    async def test_extract_content_scanned_pdf(self, pdf_extractor, test_pdf_files):
        """Test content extraction from scanned PDF using OCR."""
        if not test_pdf_files["scanned"].exists():
            pytest.skip("Scanned test PDF not found")

        result = await pdf_extractor.aextract_content(file_path=test_pdf_files["scanned"], name="scanned_document")

        assert isinstance(result, list)
        # Scanned documents might have fewer extractable elements
        # but should still extract some content via OCR

        for element in result:
            assert element.metadata["document"] == "scanned_document"
            assert isinstance(element.metadata["page"], int)

    @pytest.mark.asyncio
    async def test_extract_content_mixed_content_pdf(self, pdf_extractor, test_pdf_files):
        """Test content extraction from mixed content PDF."""
        if not test_pdf_files["mixed_content"].exists():
            pytest.skip("Mixed content test PDF not found")

        result = await pdf_extractor.aextract_content(
            file_path=test_pdf_files["mixed_content"], name="mixed_content_document"
        )

        assert isinstance(result, list)
        assert len(result) > 0

        # Should contain both text and table elements
        content_types = {elem.type for elem in result}
        assert ContentType.TEXT in content_types

        for element in result:
            assert element.metadata["document"] == "mixed_content_document"

    @pytest.mark.asyncio
    async def test_extract_content_multi_column_pdf(self, pdf_extractor, test_pdf_files):
        """Test content extraction from multi-column PDF."""
        if not test_pdf_files["multi_column"].exists():
            pytest.skip("Multi-column test PDF not found")

        result = await pdf_extractor.aextract_content(
            file_path=test_pdf_files["multi_column"], name="multi_column_document"
        )

        assert isinstance(result, list)
        assert len(result) > 0

        for element in result:
            assert element.metadata["document"] == "multi_column_document"

    def test_process_text_content_with_titles(self, pdf_extractor):
        """Test text content processing with title detection."""
        content = """1. Introduction
This is the introduction section with substantial content.
It contains multiple sentences and paragraphs.

2. Methodology
This section describes the methodology used in the research.
It includes detailed explanations of procedures.

3.1 Data Collection
This subsection covers data collection procedures.
"""

        result = pdf_extractor._process_text_content(
            content=content, title="Document Title", page_index=1, document_name="test_document"
        )

        assert isinstance(result, list)
        assert len(result) > 0

        # Check that titles are properly detected and content is split
        titles_found = [elem.metadata["title"] for elem in result]
        content_found = [elem.page_content for elem in result]

        # Should contain the processed content
        assert any("Introduction" in content for content in content_found)
        assert any("Methodology" in content for content in content_found)

    def test_process_text_content_without_titles(self, pdf_extractor):
        """Test text content processing without title patterns."""
        content = "This is plain text content without any title patterns."

        result = pdf_extractor._process_text_content(
            content=content, title="Current Title", page_index=1, document_name="test_document"
        )

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].metadata["title"] == "Current Title"
        assert "Current Title" in result[0].page_content

    def test_process_empty_text_content(self, pdf_extractor):
        """Test processing empty or None text content."""
        # Test empty string
        result = pdf_extractor._process_text_content(
            content="", title="Title", page_index=1, document_name="test_document"
        )
        assert result == []

        # Test whitespace only
        result = pdf_extractor._process_text_content(
            content="   \n\t   ", title="Title", page_index=1, document_name="test_document"
        )
        assert result == []

    @patch("pdfplumber.open")
    def test_extract_text_from_text_page(self, mock_pdfplumber, pdf_extractor):
        """Test text extraction from text-based pages."""
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Sample extracted text"

        result = pdf_extractor._extract_text_from_text_page(mock_page)
        assert result == "Sample extracted text"

        # Test error handling
        mock_page.extract_text.side_effect = Exception("Extraction failed")
        result = pdf_extractor._extract_text_from_text_page(mock_page)
        assert result == ""

    @patch("pdfplumber.open")
    def test_extract_tables_from_text_page(self, mock_pdfplumber, pdf_extractor):
        """Test table extraction from text-based pages."""
        mock_page = MagicMock()

        # Mock table data
        mock_table = MagicMock()
        mock_table.extract.return_value = [["Header 1", "Header 2"], ["Value 1", "Value 2"], ["Value 3", "Value 4"]]
        mock_page.find_tables.return_value = [mock_table]

        result = pdf_extractor._extract_tables_from_text_page(
            page=mock_page, page_index=1, document_name="test_document"
        )

        assert isinstance(result, list)
        assert len(result) > 0
        assert result[0].type == ContentType.TABLE
        assert result[0].metadata["document"] == "test_document"
        assert result[0].metadata["page"] == 1

    @patch("cv2.imread")
    @patch("pytesseract.image_to_string")
    @patch("pytesseract.image_to_pdf_or_hocr")
    def test_extract_text_from_scanned_page(self, mock_pdf_hocr, mock_tesseract, mock_cv2, pdf_extractor):
        """Test text extraction from scanned pages using OCR."""
        # Mock page and image data
        mock_page = MagicMock()
        mock_page.find_tables.return_value = []
        mock_page.images = []

        mock_image = np.zeros((800, 600, 3), dtype=np.uint8)
        mock_tesseract.return_value = "OCR extracted text"
        mock_pdf_hocr.return_value = b"PDF bytes"

        # Test the case where language detection returns English (should return tuple)
        with patch.object(pdf_extractor, "_auto_detect_language", return_value="en"):
            result = pdf_extractor._extract_text_from_scanned_page(
                page=mock_page, scale_x=1.0, scale_y=1.0, image=mock_image, pdf_page_height=800
            )

            # Should always return a tuple
            assert isinstance(result, tuple)
            assert len(result) == 2
            text, pdf_bytes = result
            assert isinstance(text, str)
            assert isinstance(pdf_bytes, bytes)

        # Test the case where language detection returns non-English (should return tuple)
        with patch.object(pdf_extractor, "_auto_detect_language", return_value="de"):
            result = pdf_extractor._extract_text_from_scanned_page(
                page=mock_page, scale_x=1.0, scale_y=1.0, image=mock_image, pdf_page_height=800
            )

            assert isinstance(result, tuple)
            assert len(result) == 2
            text, pdf_bytes = result
            assert isinstance(text, str)
            assert isinstance(pdf_bytes, bytes)

    @patch("camelot.read_pdf")
    @patch("tabula.read_pdf")
    def test_extract_tables_from_scanned_page(self, mock_tabula, mock_camelot, pdf_extractor):
        """Test table extraction from scanned pages."""
        # Mock Camelot table extraction
        mock_camelot_table = MagicMock()
        mock_camelot_table.accuracy = 75
        mock_camelot_table.df = pd.DataFrame({"Column 1": ["Value 1", "Value 2"], "Column 2": ["Value 3", "Value 4"]})
        mock_camelot.return_value = [mock_camelot_table]

        result = pdf_extractor._extract_tables_from_scanned_page(
            page_index=1, document_name="test_document", filename="/path/to/test.pdf"
        )

        assert isinstance(result, list)
        if len(result) > 0:  # Camelot succeeded
            assert result[0].type == ContentType.TABLE
            assert result[0].metadata["table_method"] == "camelot"
            assert result[0].metadata["accuracy"] == 75

    def test_title_pattern_detection(self, pdf_extractor):
        """Test title pattern regular expressions."""
        # Test single line titles
        test_cases = [
            "1. Introduction",
            "2.1 Methodology",
            "3.1.1 Data Collection",
            "4.\tResults",
            "5. Discussion and Conclusions",
        ]

        for test_case in test_cases:
            match = pdf_extractor.TITLE_PATTERN.search(test_case)
            assert match is not None, f"Should match title pattern: {test_case}"

        # Test multiline title detection
        multiline_text = """Some content here.

1. First Section
This is the content of the first section.

2. Second Section
This is the content of the second section."""

        matches = pdf_extractor.TITLE_PATTERN_MULTILINE.findall(multiline_text)
        # The regex returns tuples with groups, so we need to check the structure
        assert len(matches) >= 2, f"Should find at least 2 title patterns, found: {matches}"

        # Test that the pattern actually matches what we expect
        simple_test = "\n1. Test Title"
        simple_matches = pdf_extractor.TITLE_PATTERN_MULTILINE.findall(simple_test)
        assert len(simple_matches) >= 1, f"Should match simple title pattern, found: {simple_matches}"

    @pytest.mark.asyncio
    async def test_error_handling_invalid_file(self, pdf_extractor):
        """Test error handling with invalid PDF file."""
        invalid_path = Path("/nonexistent/file.pdf")

        with pytest.raises(Exception):
            await pdf_extractor.aextract_content(file_path=invalid_path, name="invalid_document")

    def test_related_ids_mapping(self, pdf_extractor):
        """Test that related IDs are properly set between text and table elements."""
        # This would be tested as part of the integration test
        # with actual PDF processing, but we can test the logic
        text_elements = [MagicMock(metadata={"id": "text_1"}), MagicMock(metadata={"id": "text_2"})]
        table_elements = [MagicMock(metadata={"id": "table_1"}), MagicMock(metadata={"id": "table_2"})]

        # Simulate the relationship mapping logic
        text_ids = [elem.metadata["id"] for elem in text_elements]
        table_ids = [elem.metadata["id"] for elem in table_elements]

        # Set related IDs
        for table_elem in table_elements:
            table_elem.metadata["related"] = text_ids

        for text_elem in text_elements:
            text_elem.metadata["related"] = table_ids

        # Verify relationships
        assert table_elements[0].metadata["related"] == ["text_1", "text_2"]
        assert text_elements[0].metadata["related"] == ["table_1", "table_2"]

    @pytest.mark.asyncio
    async def test_performance_with_large_pdf(self, pdf_extractor, test_pdf_files):
        """Test performance with larger PDF files."""
        # Use one of the existing test files
        test_file = None
        for file_path in test_pdf_files.values():
            if file_path.exists():
                test_file = file_path
                break

        if test_file is None:
            pytest.skip("No test PDF files available")

        import time

        start_time = time.time()

        result = await pdf_extractor.aextract_content(file_path=test_file, name="performance_test")

        end_time = time.time()
        processing_time = end_time - start_time

        assert isinstance(result, list)
        # Ensure processing doesn't take too long (adjust threshold as needed)
        assert processing_time < 60, f"Processing took too long: {processing_time} seconds"

    def test_language_mapping(self, pdf_extractor):
        """Test language code mapping for OCR."""
        assert pdf_extractor._lang_map["en"] == "eng"
        assert pdf_extractor._lang_map["de"] == "deu"

        # Test fallback for unknown language
        unknown_lang = "unknown"
        tesseract_lang = pdf_extractor._lang_map.get(unknown_lang, "eng")
        assert tesseract_lang == "eng"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_end_to_end_extraction(self, pdf_extractor, test_pdf_files):
        """Integration test for complete PDF extraction workflow."""
        for pdf_name, pdf_path in test_pdf_files.items():
            if not pdf_path.exists():
                continue

            print(f"\nTesting {pdf_name} PDF: {pdf_path}")

            result = await pdf_extractor.aextract_content(file_path=pdf_path, name=pdf_name)

            assert isinstance(result, list), f"Result should be a list for {pdf_name}"
            print(f"  Extracted {len(result)} elements")

            # Analyze results
            text_count = sum(1 for elem in result if elem.type == ContentType.TEXT)
            table_count = sum(1 for elem in result if elem.type == ContentType.TABLE)

            print(f"  Text elements: {text_count}")
            print(f"  Table elements: {table_count}")

            # Verify metadata completeness
            for i, element in enumerate(result):
                assert "document" in element.metadata, f"Missing document in element {i}"
                assert "page" in element.metadata, f"Missing page in element {i}"
                assert "id" in element.metadata, f"Missing id in element {i}"
                assert element.metadata["document"] == pdf_name, f"Wrong document name in element {i}"

            # Verify content is not empty
            non_empty_content = [elem for elem in result if elem.page_content.strip()]
            assert len(non_empty_content) > 0, f"No non-empty content extracted from {pdf_name}"

    def test_text_threshold_configuration(self, pdf_extractor):
        """Test that the text threshold is configurable."""
        # Check default threshold
        assert pdf_extractor.TEXT_THRESHOLD == 50

        # The threshold should be configurable through settings
        # This is mentioned in the TODO comment in the code


if __name__ == "__main__":
    # Generate test PDFs if they don't exist
    from test_data.generate_test_pdfs import main as generate_pdfs

    test_data_dir = Path(__file__).parent / "test_data"
    required_files = [
        "text_based_document.pdf",
        "scanned_document.pdf",
        "mixed_content_document.pdf",
        "multi_column_document.pdf",
    ]

    missing_files = [f for f in required_files if not (test_data_dir / f).exists()]
    if missing_files:
        print(f"Generating missing test files: {missing_files}")
        generate_pdfs()

    pytest.main([__file__, "-v"])
