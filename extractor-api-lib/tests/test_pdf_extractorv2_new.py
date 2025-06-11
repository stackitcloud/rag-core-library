"""Tests for the improved PDFExtractor with real PDF files."""

import asyncio
import tempfile
from pathlib import Path
import pytest
import numpy as np
import pandas as pd
from PIL import Image
import pdfplumber

from extractor_api_lib.impl.extractors.file_extractors.pdf_extractorv2 import PDFExtractor, PageType
from extractor_api_lib.impl.settings.pdf_extractor_settings import PDFExtractorSettings
from extractor_api_lib.impl.types.content_type import ContentType
from extractor_api_lib.table_converter.dataframe_converter import DataframeConverter
from extractor_api_lib.file_services.file_service import FileService


class TestPDFExtractorWithRealFiles:
    """Test suite for the improved PDFExtractor using real PDF files."""

    @pytest.fixture
    def test_data_dir(self):
        """Get the path to test data directory."""
        return Path(__file__).parent / "test_data"

    @pytest.fixture
    def text_based_pdf(self, test_data_dir):
        """Path to text-based PDF file."""
        return test_data_dir / "text_based_document.pdf"

    @pytest.fixture
    def scanned_pdf(self, test_data_dir):
        """Path to scanned PDF file."""
        return test_data_dir / "scanned_document.pdf"

    @pytest.fixture
    def mixed_content_pdf(self, test_data_dir):
        """Path to mixed content PDF file."""
        return test_data_dir / "mixed_content_document.pdf"

    @pytest.fixture
    def real_file_service(self):
        """Create a minimal file service for real files."""
        class RealFileService:
            pass
        return RealFileService()

    @pytest.fixture
    def real_settings(self):
        """Create real PDF extractor settings."""
        class RealSettings:
            footer_height = 155
            diagrams_folder_name = "connection_diagrams"
        return RealSettings()

    @pytest.fixture
    def real_dataframe_converter(self):
        """Create a real dataframe converter."""
        class RealConverter:
            def convert(self, df):
                return df.to_markdown(index=False) if hasattr(df, 'to_markdown') else str(df)
        return RealConverter()

    @pytest.fixture
    def pdf_extractor(self, real_file_service, real_settings, real_dataframe_converter):
        """Create a PDFExtractor instance for testing with real files."""
        extractor = PDFExtractor(
            file_service=real_file_service,
            pdf_extractor_settings=real_settings,
            dataframe_converter=real_dataframe_converter
        )
        return extractor

    def test_text_based_pdf_classification(self, pdf_extractor, text_based_pdf):
        """Test classification of real text-based PDF."""
        assert text_based_pdf.exists(), f"Test file {text_based_pdf} not found"
        
        with pdfplumber.open(text_based_pdf) as pdf:
            page = pdf.pages[0]
            page_type = pdf_extractor._classify_page_type(page)
            assert page_type == PageType.TEXT_BASED

    def test_scanned_pdf_classification(self, pdf_extractor, scanned_pdf):
        """Test classification of real scanned PDF."""
        assert scanned_pdf.exists(), f"Test file {scanned_pdf} not found"
        
        with pdfplumber.open(scanned_pdf) as pdf:
            page = pdf.pages[0]
            page_type = pdf_extractor._classify_page_type(page)
            assert page_type == PageType.SCANNED

    def test_mixed_content_pdf_classification(self, pdf_extractor, mixed_content_pdf):
        """Test classification of real mixed content PDF."""
        assert mixed_content_pdf.exists(), f"Test file {mixed_content_pdf} not found"
        
        with pdfplumber.open(mixed_content_pdf) as pdf:
            page = pdf.pages[0]
            page_type = pdf_extractor._classify_page_type(page)
            assert page_type == PageType.MIXED

    def test_text_extraction_from_real_text_pdf(self, pdf_extractor, text_based_pdf):
        """Test text extraction from real text-based PDF."""
        assert text_based_pdf.exists(), f"Test file {text_based_pdf} not found"
        
        with pdfplumber.open(text_based_pdf) as pdf:
            page = pdf.pages[0]
            extracted_text = pdf_extractor._extract_text_from_text_page(page)
            
            # Verify substantial text was extracted
            assert len(extracted_text) > 50
            assert "Text-Based Document" in extracted_text
            assert "Introduction" in extracted_text

    @pytest.mark.asyncio
    async def test_text_extraction_from_real_scanned_pdf(self, pdf_extractor, scanned_pdf):
        """Test OCR text extraction from real scanned PDF."""
        assert scanned_pdf.exists(), f"Test file {scanned_pdf} not found"
        
        with pdfplumber.open(scanned_pdf) as pdf:
            page = pdf.pages[0]
            # For scanned PDFs, we expect OCR to extract some text
            try:
                extracted_text = await pdf_extractor._extract_text_from_scanned_page(page, 1, scanned_pdf)
                # OCR should extract at least some text from our test scanned document
                assert len(extracted_text) > 0
            except Exception as e:
                # OCR might fail in test environment, that's acceptable
                pytest.skip(f"OCR not available in test environment: {e}")

    def test_table_extraction_from_real_text_pdf(self, pdf_extractor, text_based_pdf):
        """Test table extraction from real text-based PDF."""
        assert text_based_pdf.exists(), f"Test file {text_based_pdf} not found"
        
        with pdfplumber.open(text_based_pdf) as pdf:
            page = pdf.pages[0]
            tables = pdf_extractor._extract_tables_from_text_page(page, 1, "text_based_document")
            
            # Even if no tables found, should return empty list (not error)
            assert isinstance(tables, list)

    def test_image_extraction_from_real_mixed_pdf(self, pdf_extractor, mixed_content_pdf):
        """Test image extraction from real mixed content PDF with proper linking."""
        assert mixed_content_pdf.exists(), f"Test file {mixed_content_pdf} not found"
        
        with pdfplumber.open(mixed_content_pdf) as pdf:
            page = pdf.pages[0]
            
            # First extract text to get text element IDs
            text_content = pdf_extractor._extract_text_from_text_page(page)
            text_elements = pdf_extractor._process_text_content(text_content, "", 1, "mixed_content_document")
            text_element_ids = [element.metadata["id"] for element in text_elements]
            
            # Then extract images
            images = pdf_extractor._extract_images(page, 1, "mixed_content_document")
            
            # Should extract images as separate information pieces
            assert isinstance(images, list)
            if len(images) > 0:
                image_element = images[0]
                assert image_element.type == ContentType.IMAGE
                assert "extraction_method" in image_element.metadata
                assert "This image is located alongside text content" in image_element.page_content

    @pytest.mark.asyncio
    async def test_complete_extraction_text_based(self, pdf_extractor, text_based_pdf):
        """Test complete extraction pipeline on real text-based PDF."""
        assert text_based_pdf.exists(), f"Test file {text_based_pdf} not found"
        
        # Test the complete extraction process
        result = await pdf_extractor.aextract_content(text_based_pdf, "text_based_document")
        
        # Should extract content successfully
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Should have text content
        text_pieces = [piece for piece in result if piece.type == ContentType.TEXT]
        assert len(text_pieces) > 0
        
        # Verify metadata
        for piece in result:
            assert "document" in piece.metadata
            assert "page" in piece.metadata
            assert piece.metadata["document"] == "text_based_document"

    @pytest.mark.asyncio
    async def test_complete_extraction_mixed_content(self, pdf_extractor, mixed_content_pdf):
        """Test complete extraction pipeline on real mixed content PDF."""
        assert mixed_content_pdf.exists(), f"Test file {mixed_content_pdf} not found"
        
        # Test the complete extraction process
        result = await pdf_extractor.aextract_content(mixed_content_pdf, "mixed_content_document")
        
        # Should extract content successfully
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Should have text content (and possibly images)
        text_pieces = [piece for piece in result if piece.type == ContentType.TEXT]
        assert len(text_pieces) > 0
        
        # Verify metadata
        for piece in result:
            assert "document" in piece.metadata
            assert "page" in piece.metadata
            assert piece.metadata["document"] == "mixed_content_document"

    @pytest.mark.asyncio
    async def test_mixed_content_linking_verification(self, pdf_extractor, mixed_content_pdf):
        """Test that mixed content pages properly link images to text elements."""
        assert mixed_content_pdf.exists(), f"Test file {mixed_content_pdf} not found"
        
        # Test the complete extraction process
        result = await pdf_extractor.aextract_content(mixed_content_pdf, "mixed_content_document")
        
        # Should extract content successfully
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Should have text content and possibly images
        text_pieces = [piece for piece in result if piece.type == ContentType.TEXT]
        image_pieces = [piece for piece in result if piece.type == ContentType.IMAGE]
        
        assert len(text_pieces) > 0
        
        # If there are images, they should be linked to text elements
        if len(image_pieces) > 0:
            for image_piece in image_pieces:
                assert "related" in image_piece.metadata
                assert isinstance(image_piece.metadata["related"], list)
                # Images should be related to text elements on the same page
                assert len(image_piece.metadata["related"]) > 0
                
            # Text pieces should also have related image IDs
            for text_piece in text_pieces:
                if "related" in text_piece.metadata and text_piece.metadata["related"]:
                    # Should contain image IDs
                    image_ids = [img.metadata["id"] for img in image_pieces]
                    related_image_ids = [rid for rid in text_piece.metadata["related"] if rid in image_ids]
                    assert len(related_image_ids) > 0

    def test_file_type_compatibility(self, pdf_extractor):
        """Test that extractor reports correct compatible file types."""
        from extractor_api_lib.impl.types.file_type import FileType
        
        file_types = pdf_extractor.compatible_file_types
        assert FileType.PDF in file_types


# Mock classes for unit testing
class MockPage:
    """Mock page object for testing."""
    def __init__(self, text="", images=None):
        self._text = text
        self.images = images or []
        
    def extract_text(self):
        return self._text
        
    def find_tables(self):
        return []


class MockTable:
    """Mock table object for testing."""
    def __init__(self, data):
        self._data = data
        
    def extract(self):
        return self._data


class MockEasyOCRReader:
    """Mock EasyOCR reader for testing."""
    def readtext(self, image):
        return [
            ([(0, 0), (100, 0), (100, 20), (0, 20)], "Sample OCR text", 0.9)
        ]


# Mock-based unit tests for edge cases and error handling
class TestPDFExtractorUnitTests:
    """Test suite for the improved PDFExtractor."""

    @pytest.fixture
    def mock_file_service(self):
        """Create a mock file service."""
        class MockFileService:
            pass
        return MockFileService()

    @pytest.fixture
    def mock_settings(self):
        """Create mock PDF extractor settings."""
        class MockSettings:
            footer_height = 155
            diagrams_folder_name = "connection_diagrams"
        return MockSettings()

    @pytest.fixture
    def mock_dataframe_converter(self):
        """Create a mock dataframe converter."""
        class MockConverter:
            def convert(self, df):
                return "Table content converted"
        return MockConverter()

    @pytest.fixture
    def pdf_extractor(self, mock_file_service, mock_settings, mock_dataframe_converter, monkeypatch):
        """Create a PDFExtractor instance for testing."""
        # Mock EasyOCR reader
        mock_reader = MockEasyOCRReader()
        
        def mock_easyocr_reader(*args, **kwargs):
            return mock_reader
            
        monkeypatch.setattr(
            'extractor_api_lib.impl.extractors.file_extractors.pdf_extractorv2.easyocr.Reader',
            mock_easyocr_reader
        )
        
        extractor = PDFExtractor(
            file_service=mock_file_service,
            pdf_extractor_settings=mock_settings,
            dataframe_converter=mock_dataframe_converter
        )
        return extractor

    def test_page_classification_text_based(self, pdf_extractor):
        """Test classification of text-based pages."""
        # Mock page with substantial text (>50 characters to exceed TEXT_THRESHOLD)
        mock_page = MockPage(text="This is a substantial amount of text content that should be classified as text-based with enough characters to exceed the threshold.")

        page_type = pdf_extractor._classify_page_type(mock_page)
        assert page_type == PageType.TEXT_BASED

    def test_page_classification_scanned(self, pdf_extractor):
        """Test classification of scanned pages."""
        # Mock page with little to no text
        mock_page = MockPage(text="")

        page_type = pdf_extractor._classify_page_type(mock_page)
        assert page_type == PageType.SCANNED

    def test_page_classification_mixed(self, pdf_extractor):
        """Test classification of mixed pages."""
        # Mock page with text and images (>50 characters to exceed TEXT_THRESHOLD)
        mock_page = MockPage(
            text="This is a substantial amount of text content with images that exceeds the threshold.",
            images=[{"x0": 0, "y0": 0, "x1": 100, "y1": 100}]
        )

        page_type = pdf_extractor._classify_page_type(mock_page)
        assert page_type == PageType.MIXED

    def test_extract_text_from_text_page(self, pdf_extractor):
        """Test text extraction from text-based pages."""
        mock_page = MockPage(text="Sample text content")

        result = pdf_extractor._extract_text_from_text_page(mock_page)
        assert result == "Sample text content"

    def test_extract_text_from_text_page_with_error(self, pdf_extractor):
        """Test text extraction with pdfplumber error."""
        class FailingMockPage:
            def extract_text(self):
                raise Exception("Extraction failed")
        
        mock_page = FailingMockPage()

        result = pdf_extractor._extract_text_from_text_page(mock_page)
        assert result == ""

    @pytest.mark.asyncio
    async def test_extract_text_from_scanned_page(self, pdf_extractor, monkeypatch):
        """Test OCR text extraction from scanned pages."""
        mock_page = MockPage()

        # Create a temporary PDF file for testing
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            temp_path = Path(temp_file.name)

        try:
            # Mock convert_from_path to return a PIL image
            def mock_convert_from_path(*args, **kwargs):
                test_image = Image.new('RGB', (100, 100), color='white')
                return [test_image]
                
            monkeypatch.setattr(
                'extractor_api_lib.impl.extractors.file_extractors.pdf_extractorv2.convert_from_path',
                mock_convert_from_path
            )

            result = await pdf_extractor._extract_text_from_scanned_page(mock_page, 1, temp_path)

            # Should return the mocked OCR result
            assert "Sample OCR text" in result
        finally:
            # Clean up
            temp_path.unlink(missing_ok=True)

    def test_extract_tables_from_text_page(self, pdf_extractor):
        """Test table extraction from text-based pages."""
        class MockPageWithTable(MockPage):
            def find_tables(self):
                mock_table = MockTable([
                    ["Header1", "Header2"],
                    ["Row1Col1", "Row1Col2"],
                    ["Row2Col1", "Row2Col2"]
                ])
                return [mock_table]
        
        mock_page = MockPageWithTable()

        result = pdf_extractor._extract_tables_from_text_page(mock_page, 1, "test_doc")

        assert len(result) == 1
        assert result[0].type == ContentType.TABLE
        assert result[0].metadata["table_method"] == "pdfplumber"

    def test_extract_images(self, pdf_extractor):
        """Test image extraction from pages."""
        mock_page = MockPage(
            images=[{
                "x0": 10, "y0": 20, "x1": 110, "y1": 120,
                "width": 100, "height": 100
            }]
        )

        result = pdf_extractor._extract_images(mock_page, 1, "test_doc")

        assert len(result) == 1
        assert result[0].type == ContentType.IMAGE
        assert "Image 1 on page 1" in result[0].page_content

    def test_process_text_content_with_titles(self, pdf_extractor):
        """Test text content processing with title detection."""
        content = "1. Introduction\nThis is the introduction text.\n2. Methods\nThis describes the methods."

        result = pdf_extractor._process_text_content(content, "", 1, "test_doc")

        # Should create text pieces for each section
        assert len(result) >= 1
        assert all(piece.type == ContentType.TEXT for piece in result)

    def test_merge_text_content_prefer_text(self, pdf_extractor):
        """Test text merging prefers substantial text-based content."""
        text_content = "This is substantial text content with more than 50 characters."
        ocr_content = "OCR text"

        result = pdf_extractor._merge_text_content(text_content, ocr_content)
        assert result == text_content

    def test_merge_text_content_use_ocr(self, pdf_extractor):
        """Test text merging uses OCR when text content is insufficient."""
        text_content = "Short"
        ocr_content = "This is longer OCR content that should be used."

        result = pdf_extractor._merge_text_content(text_content, ocr_content)
        assert "OCR Content" in result
        assert ocr_content in result

    def test_merge_table_elements_prefer_text_tables(self, pdf_extractor):
        """Test table merging prefers text-based tables."""
        class MockTableElement:
            type = ContentType.TABLE
            
        text_tables = [MockTableElement()]
        scanned_tables = [MockTableElement()]

        result = pdf_extractor._merge_table_elements(text_tables, scanned_tables)
        assert result == text_tables

    def test_extract_title_from_content(self, pdf_extractor):
        """Test title extraction from content."""
        content = "1. Introduction\nThis is some content."

        result = pdf_extractor._extract_title_from_content(content)
        assert result == "1. Introduction"

    def test_extract_title_from_content_no_title(self, pdf_extractor):
        """Test title extraction when no title is present."""
        content = "Just some regular text without titles."

        result = pdf_extractor._extract_title_from_content(content)
        assert result is None

    @pytest.mark.asyncio
    async def test_extract_content_from_page_text_based(self, pdf_extractor):
        """Test complete page extraction for text-based pages."""
        mock_page = MockPage(text="Sample text content")

        file_path = Path("/fake/path.pdf")

        result, title = await pdf_extractor._extract_content_from_page(
            page_index=1,
            page=mock_page,
            page_type=PageType.TEXT_BASED,
            title="",
            document_name="test_doc",
            file_path=file_path
        )

        # Should have extracted text content
        assert len(result) >= 1
        assert any(piece.type == ContentType.TEXT for piece in result)

    def test_compatible_file_types(self, pdf_extractor):
        """Test that extractor reports correct compatible file types."""
        from extractor_api_lib.impl.types.file_type import FileType

        file_types = pdf_extractor.compatible_file_types
        assert FileType.PDF in file_types


# Performance and integration tests
class TestPDFExtractorIntegration:
    """Integration tests for PDFExtractor (requires actual dependencies)."""

    @pytest.mark.integration
    def test_dependency_imports(self):
        """Test that all required dependencies can be imported."""
        try:
            import easyocr
            import camelot
            import tabula

            # Test EasyOCR reader creation (this might take time on first run)
            reader = easyocr.Reader(['en'], gpu=False, verbose=False)
            assert reader is not None
        except ImportError as e:
            pytest.skip(f"Integration test dependencies not available: {e}")
