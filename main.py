from pathlib import Path
from collections import OrderedDict
import re
from pypdf import PdfReader
import os
from PIL import Image
import io
from openai import OpenAI
import base64
client = OpenAI()

OCR_PROMPT = "The image is a scan of a page from a handwritten journal from approximately 1776. The text is in French or English of the period. Extract the text from the image and return it as a markdown formatted string. If there is no text, return an empty string. Do not enclose the text in a markdown environment or triple quotes, just provide the minimal markdown required to retain the formatting."
TRANSLATION_PROMPT = "You are working as an acamedic historian. Translate the following markdown formatted text from 18th century French to English, preserving the original meaning and intent. Retain the markdown formatting. If there is no text, return an empty string."

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def extract_text(image_path):
    base64_image = encode_image(image_path)
    response = client.responses.create(
        model="gpt-4o",
        input=[{ "role": "user", "content": [{
                "type": "input_text",
                "text": OCR_PROMPT
            },
            {
                "type": "input_image",
                "image_url": f"data:image/jpeg;base64,{base64_image}",
            },
        ],
        }]
    )
    return response.output_text if response.output_text else ""

def translate_text(text: str):
    if len(text) < 1:
        return ""
    response = client.responses.create(
        instructions=TRANSLATION_PROMPT,
        model="gpt-4o",
        input=text
    )
    return response.output_text

def natural_sort_key(s: str) -> list:
    """
    Create a key for natural sorting of strings containing numbers.
    Example: "part 2" -> ["part ", 2]
    """
    def convert(text):
        return int(text) if text.isdigit() else text.lower()
    return [convert(c) for c in re.split('([0-9]+)', s)]

def find_pdf_files() -> OrderedDict[str, Path]:
    """
    Find all PDF files in the data directory and return them as an ordered dictionary.
    The key is the filename without extension, and the value is the full path.
    The dictionary is sorted using natural sorting (e.g., "part 2" comes before "part 10").
    """
    data_dir = Path("data")
    pdf_files = {}

    for pdf_path in data_dir.glob("*.pdf"):
        pdf_files[pdf_path.stem] = pdf_path

    return OrderedDict(sorted(pdf_files.items(), key=lambda x: natural_sort_key(x[0])))


def extract_images(pdf_path: Path, scale: float = 1.0, override_text: bool = False):
    """
    Extract images from a PDF file and save them as JPG files.
    Images are saved in a directory named after the PDF file.

    Args:
        pdf_path: Path to the PDF file
        scale: Scaling factor for the images (e.g., 0.5 for half size)
        override_text: If True, always extract text even if markdown file exists
    """
    if scale <= 0 or scale > 1:
        raise ValueError("Scale must be between 0 and 1")

    # Create output directory based on PDF filename
    output_dir = Path("images") / pdf_path.stem
    output_dir.mkdir(parents=True, exist_ok=True)

    html_input = []

    reader = PdfReader(pdf_path)
    for page_num, page in enumerate(reader.pages, start=1):
        if page_num > 5:
            break
        for img_num, image_file_object in enumerate(page.images, start=1):
            # Create filename: page_number-image_number.jpg
            img_filename = f"page{page_num:04d}-image{img_num}.jpg"
            img_path = output_dir / img_filename


            # Load image data into PIL Image
            img = Image.open(io.BytesIO(image_file_object.data))

            # Apply scaling if needed
            if scale < 1.0:
                new_size = (int(img.width * scale), int(img.height * scale))
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            # convert to greyscale
            img = img.convert("L")

            # Save the image
            img.save(img_path, "JPEG", quality=95)
            print(f"Saved image: {img_path} (original size: {img.width}x{img.height})")

            # convert to markdown
            text_path = img_path.with_stem(img_path.stem + "_french").with_suffix(".md")
            if override_text or not text_path.exists():
                print(f"Extracting text from {img_path}")
                text = extract_text(img_path)
                with open(text_path, "w") as f:
                    f.write(text)
            else:
                with open(text_path, "r") as f:
                    text = f.read()

            # translate text
            translated_text_path = img_path.with_stem(img_path.stem + "_english").with_suffix(".md")
            if not translated_text_path.exists():
                print(f"Translating text from {text_path} to {translated_text_path}")
                translated_text = translate_text(text)
                with open(translated_text_path, "w") as f:
                    f.write(translated_text)

            html_input.append((img_path, text_path, translated_text_path))

    create_html_document(html_input, output_dir / f"{pdf_path.stem}.html")

def create_html_document(pages: list[tuple[Path, Path, Path]], output_path: Path):
    """
    Create an HTML document with multiple pages, each containing three columns:
    image, French text, and English text.

    Args:
        pages: List of 3-tuples containing (image_path, french_md_path, english_md_path)
        output_path: Path where the HTML file should be saved
    """
    import markdown2
    from weasyprint import HTML, CSS

    # HTML template with CSS styling
    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Document Viewer</title>
    <style>
        @page {{
            size: A4 landscape;
            margin: 1cm;
        }}
        body {{
            margin: 0;
            padding: 0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
        }}
        .page {{
            display: flex;
            min-height: 100vh;
            border-bottom: 2px solid #ccc;
            padding: 2rem;
            box-sizing: border-box;
            page-break-after: always;
        }}
        .column {{
            flex: 1;
            padding: 1rem;
            overflow-y: auto;
            max-height: calc(100vh - 4rem);
            display: flex;
            flex-direction: column;
        }}
        .column + .column {{
            border-left: 1px solid #ccc;
        }}
        .image-container {{
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 0;
            padding: 1rem;
        }}
        .image-container img {{
            max-width: 100%;
            max-height: 100%;
            width: auto;
            height: auto;
            object-fit: contain;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .text-container {{
            background: #fff;
            padding: 1rem;
        }}
        /* Style for markdown content */
        .markdown-body {{
            font-size: 16px;
        }}
        .markdown-body pre {{
            background-color: #f6f8fa;
            padding: 1rem;
            border-radius: 4px;
            overflow-x: auto;
        }}
        .markdown-body img {{
            max-width: 100%;
        }}
        @media print {{
            .page {{
                page-break-after: always;
            }}
        }}
    </style>
</head>
<body>
{content}
</body>
</html>
"""

    # Initialize markdown converter
    markdown = markdown2.Markdown()

    # Process each page
    content = []
    for image_path, french_md_path, english_md_path in pages:
        # Read markdown files
        with open(french_md_path, 'r', encoding='utf-8') as f:
            french_text = markdown.convert(f.read())
        with open(english_md_path, 'r', encoding='utf-8') as f:
            english_text = markdown.convert(f.read())

        # Create relative paths for images
        image_rel_path = os.path.relpath(image_path, output_path.parent)

        # Create page HTML
        page_html = f"""
    <div class="page">
        <div class="column">
            <div class="image-container">
                <img src="{image_rel_path}" alt="Original document">
            </div>
        </div>
        <div class="column">
            <div class="text-container">
                <div class="markdown-body">
                    {french_text}
                </div>
            </div>
        </div>
        <div class="column">
            <div class="text-container">
                <div class="markdown-body">
                    {english_text}
                </div>
            </div>
        </div>
    </div>"""
        content.append(page_html)

    # Combine all content
    final_html = html_template.format(content='\n'.join(content))

    # Write the HTML file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_html)

    print(f"Created HTML document with {len(pages)} pages: {output_path}")

    # Convert HTML to PDF
    pdf_path = output_path.with_suffix('.pdf')
    HTML(string=final_html).write_pdf(pdf_path)
    print(f"Created PDF document: {pdf_path}")

def main():
    pdf_files = find_pdf_files()
    for name, path in pdf_files.items():
        print(f"Processing PDF: {name}")
        extract_images(path, scale=0.5, override_text=False)  # Default to half size, no override

        import sys; sys.exit()

if __name__ == "__main__":
    main()
