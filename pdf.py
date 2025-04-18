import re
from collections import OrderedDict
from pathlib import Path
import glob
from pypdf import PdfReader

def natural_sort_key(s: str) -> list:
    """
    Create a key for natural sorting of strings containing numbers.
    Example: "part 2" -> ["part ", 2]
    """
    def convert(text):
        return int(text) if text.isdigit() else text.lower()
    return [convert(c) for c in re.split('([0-9]+)', s)]


def find_pdf_files(data_dir: Path, notebook_name: str):
    """
    Find all PDF files in the data directory and return them as an ordered dictionary.
    The key is the filename without extension, and the value is the full path.
    The list is sorted using natural sorting (e.g., "part 2" comes before "part 10").
    """
    glob_str = f"{data_dir}/{notebook_name}*.pdf"
    pdf_files = [Path(f) for f in glob.glob(glob_str)]
    sorted_files = sorted(pdf_files, key=lambda x: natural_sort_key(x.stem))
    return sorted_files

def notebook_images(sorted_pdf_files: list[Path]):
    """
    generator of images from all pdfs in a notebook
    """
    i = 1
    for pdf_file in sorted_pdf_files:
        reader = PdfReader(pdf_file)
        for page_num, page in enumerate(reader.pages, start=1):
            for img_num, image_file_object in enumerate(page.images, start=1):
                yield (i, image_file_object)
                i += 1
