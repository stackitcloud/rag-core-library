#!/usr/bin/env python3
"""Test the enhanced PDF extractor with the new PDF files."""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from extractor_api_lib.impl.extractors.file_extractors.pdf_extractorv2 import PDFExtractorV2


def test_enhanced_pdfs():
    """Test the PDF extractor with all enhanced PDF files."""
    test_data_dir = Path(__file__).parent / "test_data"
    extractor = PDFExtractorV2()

    # Test files to process
    test_files = [
        "text_based_document.pdf",
        "mixed_content_document.pdf",
        "multi_column_document.pdf",
        "scanned_document.pdf"
    ]

    results = {}

    for filename in test_files:
        file_path = test_data_dir / filename
        if file_path.exists():
            print(f"\n{'='*60}")
            print(f"Testing: {filename}")
            print(f"{'='*60}")

            try:
                # Extract content
                extracted_content = extractor.extract(str(file_path))

                # Print summary statistics
                print(f"Total content pieces: {len(extracted_content)}")

                content_types = {}
                for content in extracted_content:
                    content_type = content.content_type.value
                    content_types[content_type] = content_types.get(content_type, 0) + 1

                print("Content type distribution:")
                for content_type, count in content_types.items():
                    print(f"  - {content_type}: {count}")

                # Show text content summary
                text_contents = [c for c in extracted_content if c.content_type.value == "TEXT"]
                if text_contents:
                    total_text_length = sum(len(c.content) for c in text_contents)
                    print(f"Total text length: {total_text_length} characters")

                    # Show first text content preview
                    first_text = text_contents[0].content[:200] + "..." if len(text_contents[0].content) > 200 else text_contents[0].content
                    print(f"First text preview: {first_text}")

                # Show table content summary
                table_contents = [c for c in extracted_content if c.content_type.value == "TABLE"]
                if table_contents:
                    print(f"Tables found: {len(table_contents)}")
                    for i, table in enumerate(table_contents):
                        print(f"  Table {i+1}: {len(table.content)} characters")

                # Show image content summary
                image_contents = [c for c in extracted_content if c.content_type.value == "IMAGE"]
                if image_contents:
                    print(f"Images found: {len(image_contents)}")
                    for i, image in enumerate(image_contents):
                        print(f"  Image {i+1}: {image.content[:100]}...")

                results[filename] = {
                    "success": True,
                    "content_count": len(extracted_content),
                    "content_types": content_types
                }

            except Exception as e:
                print(f"Error processing {filename}: {e}")
                results[filename] = {
                    "success": False,
                    "error": str(e)
                }
        else:
            print(f"File not found: {file_path}")
            results[filename] = {
                "success": False,
                "error": "File not found"
            }

    # Print summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    for filename, result in results.items():
        if result["success"]:
            print(f"✅ {filename}: {result['content_count']} content pieces")
            for content_type, count in result["content_types"].items():
                print(f"   - {content_type}: {count}")
        else:
            print(f"❌ {filename}: {result['error']}")

    return results


if __name__ == "__main__":
    test_enhanced_pdfs()
