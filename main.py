from pathlib import Path
from pypdf import PdfReader
import click
from latex import create_latex_document
from process import extract_text, translate_text
from pdf import notebook_images, find_pdf_files
from image import save_page_image

def clean_text(text: str) -> str:
    """
    Remove triple backticks from the start and end of a string.
    Also remove any leading/trailing whitespace.
    """
    text = text.strip()
    if text.startswith('```'):
        text = text[3:]
    if text.endswith('```'):
        text = text[:-3]
    return text.strip()

def process_single_image(image_file_object, page_num: int, img_num: int, output_dir: Path, scale: float = 1.0, override_text: bool = False) -> tuple[Path, Path, Path]:
    """
    Process a single image from a PDF page, including saving, text extraction, and translation.

    Args:
        image_file_object: The image object from PyPDF2
        page_num: Page number in the PDF
        img_num: Image number on the page
        output_dir: Directory to save the output files
        scale: Scaling factor for the images (e.g., 0.5 for half size)
        override_text: If True, always extract text even if markdown file exists

    Returns:
        Tuple of (image_path, french_md_path, english_md_path)
    """


    # convert to markdown
    text_path = img_path.with_stem(img_path.stem + "_french").with_suffix(".md")
    if override_text or not text_path.exists():
        print(f"Extracting text from {img_path}")
        text = clean_text(extract_text(img_path))
        with open(text_path, "w") as f:
            f.write(text)
    else:
        with open(text_path, "r") as f:
            text = f.read()

    # translate text
    translated_text_path = img_path.with_stem(img_path.stem + "_english").with_suffix(".md")
    if not translated_text_path.exists():
        print(f"Translating text from {text_path} to {translated_text_path}")
        translated_text = clean_text(translate_text(text))
        with open(translated_text_path, "w") as f:
            f.write(translated_text)

    return (img_path, text_path, translated_text_path)

def extract_images(pdf_path: Path, scale: float = 1.0, override_text: bool = False, max_pages: int = None):
    """
    Extract images from a PDF file and save them as JPG files.
    Images are saved in a directory named after the PDF file.

    Args:
        pdf_path: Path to the PDF file
        scale: Scaling factor for the images (e.g., 0.5 for half size)
        override_text: If True, always extract text even if markdown file exists
        max_pages: Maximum number of pages to process (None for all pages)
    """
    if scale <= 0 or scale > 1:
        raise ValueError("Scale must be between 0 and 1")

    # Create output directory based on PDF filename
    output_dir = Path("images") / pdf_path.stem
    output_dir.mkdir(parents=True, exist_ok=True)

    latex_input = []

    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)
    if max_pages is not None:
        total_pages = min(total_pages, max_pages)
        print(f"Processing {total_pages} of {len(reader.pages)} pages")

    for page_num, page in enumerate(reader.pages[:total_pages], start=1):
        for img_num, image_file_object in enumerate(page.images, start=1):
            result = process_single_image(image_file_object, page_num, img_num, output_dir, scale, override_text)
            latex_input.append(result)

    # Create LaTeX document
    create_latex_document(latex_input, output_dir / f"{pdf_path.stem}.tex")






@click.group()
def main():
    """Process PDF files, extracting images and text."""
    pass

@main.command()
@click.argument('notebook_name', type=str)
@click.option('--scale', type=float, default=0.5, help='Scaling factor for images (0.0 to 1.0)')
def extract(notebook_name: str, scale: float):
    """Extract images from a PDF file."""
    input_dir = Path.cwd() / "input_data"
    pdf_files = find_pdf_files(input_dir, notebook_name)
    if len(pdf_files) == 0:
        raise ValueError(f"No PDF files found for {notebook_name}")

    # make the output directory if it doesn't exist
    output_dir = Path.cwd() / "output" / notebook_name
    output_dir.mkdir(parents=True, exist_ok=True)

    for i, image_file_object in notebook_images(pdf_files):
        save_page_image(image_file_object, i, output_dir, scale)

@main.command()
@click.option('--override', is_flag=True, help='Always extract text even if text file exists')
@click.option('--npages', type=int, help='Maximum number of pages to process',)
@click.option('--model', type=click.Choice(['claude', 'openai']), default='openai', help='Model to use for OCR')
@click.argument('notebook_name', type=str)
def ocr(notebook_name: str, override: bool, npages: int, model: str):
    """Perform OCR on images from a PDF file."""
    input_dir = Path.cwd() / "output" / notebook_name
    input_images = sorted(list(input_dir.glob("*.jpg")), key=lambda x: int(x.stem.split('_')[1]))
    if len(input_images) == 0:
        raise ValueError(f"No images found for {notebook_name}")

    # make the output directory if it doesn't exist
    output_dir = input_dir / f"{model}_ocr"
    output_dir.mkdir(parents=True, exist_ok=True)

    if npages is not None:
        input_images = input_images[:npages]

    for image_path in input_images:
        print(f"Processing {image_path}")
        text_path = output_dir / f"{image_path.stem}_french.txt"
        if not text_path.exists() or override:
            text = extract_text(image_path, model=model)
            with open(text_path, "w") as f:
                f.write(text)
        else:
            print(f"Text file {text_path} exists, skipping")

    #extract_images(pdf_path, override_text=override, max_pages=npages, model=model)

@main.command()
@click.option('--override', is_flag=True, help='Always extract text even if text file exists')
@click.option('--npages', type=int, help='Maximum number of pages to process',)
@click.option('--model', type=click.Choice(['claude', 'openai']), default='openai', help='Model to use for translation')
@click.option('--ocr_model', type=click.Choice(['claude', 'openai']), default=None, help='OCR data model to use')
@click.argument('notebook_name', type=str)
def translate(notebook_name: str, npages: int, model: str, ocr_model: str, override: bool):
    """Translate text from images in a PDF file."""

    if ocr_model is None:
        ocr_model = model

    input_dir = Path.cwd() / "output" / notebook_name / f"{ocr_model}_ocr"
    input_txt_files = sorted(list(input_dir.glob("*.txt")), key=lambda x: int(x.stem.split('_')[1]))
    if len(input_txt_files) == 0:
        raise ValueError(f"No OCR data found for {notebook_name}")

    output_dir = Path.cwd() / "output" / notebook_name / f"{ocr_model}_ocr_{model}_trans"
    output_dir.mkdir(parents=True, exist_ok=True)
    for input_txt_file in input_txt_files:
        output_file = output_dir / f"{input_txt_file.stem.rstrip('_french')}_english.txt"
        if not override and output_file.exists():
            print(f"Skipping {output_file} because it exists")
            continue
        print(f"Translating {input_txt_file}")
        text = input_txt_file.read_text()
        translated_text = translate_text(text, model)
        with open(output_file, "w") as f:
            f.write(translated_text)
        print(f"{input_txt_file.stem} -> {output_file.stem}")

if __name__ == "__main__":
    main()
