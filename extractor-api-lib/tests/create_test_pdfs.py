#!/usr/bin/env python3
"""Script to create test PDF files for testing the PDF extractor."""

import os
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.lib.utils import ImageReader
from PIL import Image, ImageDraw, ImageFont
import io

def create_text_based_pdf():
    """Create a PDF with substantial text content and tables."""
    output_path = Path(__file__).parent / "test_data" / "text_based_document.pdf"
    
    c = canvas.Canvas(str(output_path), pagesize=letter)
    width, height = letter
    
    # Page 1 - Text content
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "1. Introduction")
    
    c.setFont("Helvetica", 12)
    text_content = [
        "This is a comprehensive text-based document with substantial content.",
        "It contains multiple paragraphs with meaningful information that should",
        "be easily extractable using pdfplumber's text extraction capabilities.",
        "",
        "The document demonstrates various formatting elements including:",
        "- Headers and subheaders",
        "- Bullet points and lists", 
        "- Tables with structured data",
        "- Multiple pages with consistent formatting",
        "",
        "This content exceeds the 50-character threshold required for",
        "classification as a text-based page in the PDF extractor."
    ]
    
    y = height - 80
    for line in text_content:
        if line:
            c.drawString(50, y, line)
        y -= 15
    
    # Add a table
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y - 20, "2. Data Table")
    
    # Simple table representation
    y -= 50
    table_data = [
        ["Name", "Age", "Department"],
        ["Alice Smith", "28", "Engineering"],
        ["Bob Johnson", "35", "Marketing"],
        ["Carol Davis", "42", "Finance"]
    ]
    
    c.setFont("Helvetica", 10)
    for i, row in enumerate(table_data):
        x = 50
        for cell in row:
            if i == 0:  # Header
                c.setFont("Helvetica-Bold", 10)
            else:
                c.setFont("Helvetica", 10)
            c.drawString(x, y, cell)
            x += 120
        y -= 20
    
    # Page 2 - More text content
    c.showPage()
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "3. Additional Content")
    
    c.setFont("Helvetica", 12)
    more_text = [
        "This second page contains additional text content to demonstrate",
        "multi-page text extraction capabilities. The PDF extractor should",
        "be able to process each page independently and classify them",
        "correctly based on their content characteristics.",
        "",
        "Key features tested:",
        "- Page classification (text-based vs scanned vs mixed)",
        "- Text extraction accuracy",
        "- Table detection and extraction",
        "- Multi-page document handling"
    ]
    
    y = height - 80
    for line in more_text:
        if line:
            c.drawString(50, y, line)
        y -= 15
    
    c.save()
    print(f"Created text-based PDF: {output_path}")

def create_scanned_image_pdf():
    """Create a PDF that simulates a scanned document with images."""
    output_path = Path(__file__).parent / "test_data" / "scanned_document.pdf"
    
    c = canvas.Canvas(str(output_path), pagesize=letter)
    width, height = letter
    
    # Create a simulated scanned image
    img = Image.new('RGB', (int(width-100), int(height-100)), color='white')
    draw = ImageDraw.Draw(img)
    
    # Try to use a default font, fallback to basic if not available
    try:
        font = ImageFont.truetype("Arial.ttf", 16)
        title_font = ImageFont.truetype("Arial.ttf", 20)
    except:
        try:
            font = ImageFont.load_default()
            title_font = ImageFont.load_default()
        except:
            font = None
            title_font = None
    
    # Draw text on the image (simulating scanned text)
    if font:
        draw.text((50, 50), "SCANNED DOCUMENT", fill='black', font=title_font)
        draw.text((50, 100), "This document appears to be scanned.", fill='black', font=font)
        draw.text((50, 130), "Text extraction will require OCR.", fill='black', font=font)
        draw.text((50, 160), "Image content: Chart showing sales data", fill='black', font=font)
    else:
        # Fallback without font
        draw.text((50, 50), "SCANNED DOCUMENT", fill='black')
        draw.text((50, 100), "This document appears to be scanned.", fill='black')
        draw.text((50, 130), "Text extraction will require OCR.", fill='black')
        draw.text((50, 160), "Image content: Chart showing sales data", fill='black')
    
    # Add some graphical elements to simulate charts/diagrams
    draw.rectangle([50, 200, 200, 300], outline='black', width=2)
    draw.rectangle([70, 250, 90, 280], fill='blue')
    draw.rectangle([100, 230, 120, 280], fill='red') 
    draw.rectangle([130, 260, 150, 280], fill='green')
    draw.text((50, 310), "Bar Chart Example", fill='black', font=font if font else None)
    
    # Convert PIL image to reportlab format
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    
    # Add the image to PDF
    c.drawImage(ImageReader(img_buffer), 50, 50, width=width-100, height=height-100)
    
    c.save()
    print(f"Created scanned PDF: {output_path}")

def create_mixed_content_pdf():
    """Create a PDF with both extractable text and embedded images."""
    output_path = Path(__file__).parent / "test_data" / "mixed_document.pdf"
    
    c = canvas.Canvas(str(output_path), pagesize=letter)
    width, height = letter
    
    # Add extractable text content
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "Mixed Content Document")
    
    c.setFont("Helvetica", 12)
    text_lines = [
        "This document contains both extractable text and embedded images,",
        "making it a perfect test case for mixed content classification.",
        "The text portion should be extractable via pdfplumber, while",
        "the images require different handling methods.",
        "",
        "Document sections:",
        "1. Introduction (this section)",
        "2. Data visualization (chart below)",
        "3. Summary and conclusions"
    ]
    
    y = height - 80
    for line in text_lines:
        if line:
            c.drawString(50, y, line)
        y -= 15
    
    # Create and embed an image
    img = Image.new('RGB', (300, 200), color='lightblue')
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("Arial.ttf", 14)
    except:
        font = ImageFont.load_default()
    
    # Draw a simple chart
    draw.rectangle([20, 20, 280, 180], outline='black', width=2)
    draw.text((100, 30), "Sales by Quarter", fill='black', font=font)
    
    # Draw bars
    quarters = [(50, 160, 70, 100), (100, 160, 120, 80), (150, 160, 170, 60), (200, 160, 220, 90)]
    colors_list = ['red', 'blue', 'green', 'orange']
    
    for i, (x1, y1, x2, y2) in enumerate(quarters):
        draw.rectangle([x1, y2, x2, y1], fill=colors_list[i])
        draw.text((x1, y1+10), f"Q{i+1}", fill='black', font=font)
    
    # Convert to reportlab format
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    
    # Add image to PDF
    c.drawImage(ImageReader(img_buffer), 50, y - 250, width=300, height=200)
    
    # Add more text after the image
    y -= 270
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "3. Analysis Summary")
    
    c.setFont("Helvetica", 12)
    summary_text = [
        "The chart above shows quarterly sales performance with significant",
        "growth in Q3. This mixed document demonstrates the extractor's",
        "ability to handle both text and image content appropriately."
    ]
    
    y -= 20
    for line in summary_text:
        c.drawString(50, y, line)
        y -= 15
    
    c.save()
    print(f"Created mixed content PDF: {output_path}")

if __name__ == "__main__":
    print("Creating test PDF files...")
    
    # Install required dependencies if not present
    try:
        import reportlab
        from PIL import Image
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Please install: pip install reportlab Pillow")
        exit(1)
    
    create_text_based_pdf()
    create_scanned_image_pdf()
    create_mixed_content_pdf()
    
    print("All test PDF files created successfully!")
