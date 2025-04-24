import fnmatch
from pathlib import Path
from pydoc import plain
from pypdf import PdfReader
import click
from latex import create_latex_document
from process import extract_text, translate_text, format_text, analyse_text
from pdf import notebook_images, find_pdf_files
from image import save_page_image



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
    output_dir = Path.cwd() / "output" / notebook_name / "images"
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
    input_dir = Path.cwd() / "output" / notebook_name / "images"
    input_images = sorted(list(input_dir.glob("*.jpg")), key=lambda x: int(x.stem.split('_')[1]))
    if len(input_images) == 0:
        raise ValueError(f"No images found for {notebook_name}")

    # make the output directory if it doesn't exist
    output_dir = Path.cwd() / "output" / notebook_name / f"{model}_ocr"
    output_dir.mkdir(parents=True, exist_ok=True)

    if npages is not None:
        input_images = input_images[:npages]

    for image_path in input_images:
        print(f"Processing {image_path}")
        text_path = output_dir / f"{image_path.stem}_french.txt"
        latex_path = output_dir / f"{image_path.stem}_french.tex"
        text_log_path = output_dir / f"{image_path.stem}_french.txt.log"
        latex_log_path = output_dir / f"{image_path.stem}_french.tex.log"
        if not text_path.exists() or override:
            text, text_log = extract_text(image_path, model=model)
            latex, latex_log = format_text(text, model=model)
            with open(text_path, "w") as f:
                f.write(text)
            with open(latex_path, "w") as f:
                f.write(latex)
            with open(text_log_path, "w") as f:
                f.write(text_log)
            with open(latex_log_path, "w") as f:
                f.write(latex_log)
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
        latex_file = output_dir / f"{input_txt_file.stem.rstrip('_french')}_english.tex"
        text_log_file = output_dir / f"{input_txt_file.stem.rstrip('_french')}_english.txt.log"
        latex_log_file = output_dir / f"{input_txt_file.stem.rstrip('_french')}_english.tex.log"
        if not override and output_file.exists():
            print(f"Skipping {output_file} because it exists")
            continue
        print(f"Translating {input_txt_file}")
        text = input_txt_file.read_text()
        translated_text, text_log = translate_text(text, model)
        latex, latex_log = format_text(translated_text, model)
        with open(output_file, "w") as f:
            f.write(translated_text)
        with open(latex_file, "w") as f:
            f.write(latex)
        with open(text_log_file, "w") as f:
            f.write(text_log)
        with open(latex_log_file, "w") as f:
            f.write(latex_log)
        print(f"{input_txt_file.stem} -> {output_file.stem}")

@main.command()
@click.option('--model', type=click.Choice(['claude', 'openai']), default=None, help='Summarising model to use')
@click.option('--trans_model', type=click.Choice(['claude', 'openai']), default=None, help='Model to use for translation')
@click.option('--ocr_model', type=click.Choice(['claude', 'openai']), default=None, help='OCR data model to use')
@click.argument('notebook_name', type=str)
def collate(notebook_name: str, model: str, ocr_model: str, trans_model: str):
    """collate the OCR and translation text along with the original images to a pdf file compiled with latex"""

    trans_model = trans_model if trans_model is not None else model
    ocr_model = ocr_model if ocr_model is not None else model

    image_dir = Path.cwd() / "output" / notebook_name / "images"
    french_dir = Path.cwd() / "output" / notebook_name / f"{ocr_model}_ocr"
    english_dir = Path.cwd() / "output" / notebook_name / f"{ocr_model}_ocr_{trans_model}_trans"
    image_files = sorted(list(image_dir.glob("*.jpg")), key=lambda x: int(x.stem.split('_')[1]))
    french_files = sorted(list(french_dir.glob("*.tex")), key=lambda x: int(x.stem.split('_')[1]))
    english_files = sorted(list(english_dir.glob("*.tex")), key=lambda x: int(x.stem.split('_')[1]))
    plain_files = sorted(list(english_dir.glob("*.txt")), key=lambda x: int(x.stem.split('_')[1]))

    image_keys = [int(f.stem.split('_')[1]) for f in image_files]
    french_keys = [int(f.stem.split('_')[1]) for f in french_files]
    english_keys = [int(f.stem.split('_')[1]) for f in english_files]
    plain_keys = [int(f.stem.split('_')[1]) for f in plain_files]
    pages = set(image_keys).intersection(french_keys).intersection(english_keys).intersection(plain_keys)
    assert set(range(1, len(pages) + 1)) == set(pages), "Page numbers are not contiguous"
    print(f"Found {len(pages)} pages")

    # filter the files to only include the pages that exist
    image_files = [f for f in image_files if int(f.stem.split('_')[1]) in pages]
    french_files = [f for f in french_files if int(f.stem.split('_')[1]) in pages]
    english_files = [f for f in english_files if int(f.stem.split('_')[1]) in pages]
    plain_files = [f for f in plain_files if int(f.stem.split('_')[1]) in pages]

    # create the full summary
    full_text = "\n\n".join([f.read_text() for f in plain_files])
    summary, summary_log = analyse_text(full_text, model)

    # zip the files together
    latex_pages = list(zip(image_files, french_files, english_files))
    output_dir = Path.cwd() / "output" / notebook_name
    summary_log_file = output_dir / f"summary_{notebook_name}.log"
    with open(summary_log_file, 'w') as f:
        f.write(summary_log)
    create_latex_document(latex_pages, output_dir / f"{notebook_name}.tex", notebook_name, model, summary)

if __name__ == "__main__":
    main()
