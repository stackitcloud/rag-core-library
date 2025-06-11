#!/usr/bin/env python3
"""Quick test to verify PDF extractor functionality with real files."""

import asyncio
from pathlib import Path
import sys
import os

# Add the source directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from extractor_api_lib.impl.extractors.file_extractors.pdf_extractorv2 import PDFExtractor, PageType
import pdfplumber


async def test_pdf_functionality():
    """Test the PDF extractor with real files."""
    print("🔍 Testing PDF Extractor Functionality\n")

    # Test data directory
    test_data_dir = Path(__file__).parent / "test_data"

    # Check if test files exist
    text_pdf = test_data_dir / "text_based_document.pdf"
    mixed_pdf = test_data_dir / "mixed_content_document.pdf"
    scanned_pdf = test_data_dir / "scanned_document.pdf"

    print("📁 Test Files:")
    for pdf_file in [text_pdf, mixed_pdf, scanned_pdf]:
        status = "✅ EXISTS" if pdf_file.exists() else "❌ MISSING"
        print(f"  {pdf_file.name}: {status}")

    print("\n" + "="*60)

    # Create mock dependencies
    class MockFileService:
        pass

    class MockSettings:
        footer_height = 155
        diagrams_folder_name = "connection_diagrams"

    class MockConverter:
        def convert(self, df):
            return df.to_markdown(index=False) if hasattr(df, 'to_markdown') else str(df)

    # Create extractor
    extractor = PDFExtractor(
        file_service=MockFileService(),
        pdf_extractor_settings=MockSettings(),
        dataframe_converter=MockConverter()
    )

    # Test page classification with real PDFs
    print("\n🔬 Page Classification Tests:")

    for pdf_file, expected_type in [
        (text_pdf, PageType.TEXT_BASED),
        (mixed_pdf, PageType.MIXED),
        (scanned_pdf, PageType.SCANNED)
    ]:
        if pdf_file.exists():
            print(f"\n📄 Testing {pdf_file.name}:")
            try:
                with pdfplumber.open(pdf_file) as pdf:
                    page = pdf.pages[0]
                    classified_type = extractor._classify_page_type(page)

                    status = "✅ CORRECT" if classified_type == expected_type else "❌ INCORRECT"
                    print(f"  Expected: {expected_type.value}")
                    print(f"  Actual:   {classified_type.value}")
                    print(f"  Result:   {status}")

                    # Show some details
                    text = page.extract_text() or ""
                    text_length = len(text.strip())
                    has_images = len(page.images) > 0
                    print(f"  Text length: {text_length} chars")
                    print(f"  Has images: {has_images}")

            except Exception as e:
                print(f"  ❌ ERROR: {e}")
        else:
            print(f"\n📄 {pdf_file.name}: SKIPPED (file not found)")

    print("\n" + "="*60)

    # Test full extraction on mixed content PDF
    if mixed_pdf.exists():
        print("\n🚀 Full Extraction Test (Mixed Content):")
        try:
            result = await extractor.aextract_content(mixed_pdf, "mixed_test")

            print(f"  Total pieces extracted: {len(result)}")

            # Count by type
            text_pieces = [p for p in result if p.type.value == "TEXT"]
            image_pieces = [p for p in result if p.type.value == "IMAGE"]
            table_pieces = [p for p in result if p.type.value == "TABLE"]

            print(f"  Text pieces: {len(text_pieces)}")
            print(f"  Image pieces: {len(image_pieces)}")
            print(f"  Table pieces: {len(table_pieces)}")

            # Check linking
            if image_pieces and text_pieces:
                image = image_pieces[0]
                related_ids = image.metadata.get("related", [])
                print(f"  Image linking: {len(related_ids)} related elements")

                # Check if text elements have back-references
                for text_piece in text_pieces:
                    if image.metadata["id"] in text_piece.metadata.get("related", []):
                        print(f"  ✅ Bidirectional linking confirmed")
                        break
                else:
                    print(f"  ⚠️  No bidirectional linking found")

            print(f"  ✅ Full extraction successful!")

        except Exception as e:
            print(f"  ❌ ERROR: {e}")
    else:
        print(f"\n🚀 Full Extraction Test: SKIPPED (mixed PDF not found)")

    print("\n" + "="*60)
    print("🎉 PDF Extractor Test Complete!")


if __name__ == "__main__":
    asyncio.run(test_pdf_functionality())
