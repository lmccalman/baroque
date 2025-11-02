import io
import re
from pathlib import Path

from PIL import Image
from pypdf import PdfReader

import config as cfg
from base import BaroqueInputImage


def _notebook_images(sorted_pdf_files: list[Path]):
    """
    generator of images from all pdfs in a notebook
    """
    i = 1
    for pdf_file in sorted_pdf_files:
        reader = PdfReader(pdf_file)
        for _page_num, page in enumerate(reader.pages, start=1):
            for _img_num, image_file_object in enumerate(page.images, start=1):
                yield (i, image_file_object, pdf_file)
                i += 1


def import_raw_files(data_dir: Path):
    """Find the processed files for doing obsidian and things like that"""
    folders = list(Path(data_dir).glob("*/"))
    sorted_folders = sorted(folders, key=lambda x: _natural_sort_key(x.stem))

    files = {}
    for f in sorted_folders:
        key = f.name
        english_pages = sorted((data_dir / f).glob("english_page_*.txt"))
        french_pages = [
            f / ("french" + k.name.removeprefix("english")) for k in english_pages
        ]
        images = [
            f / "images" / (k.stem.removeprefix("english_") + ".jpg")
            for k in english_pages
        ]
        vals = list(zip(french_pages, english_pages, images))
        files[key] = vals
    return files


def all_files(data_dir: Path):
    """Find all pdf and image files across the whole collection, with natural
    sorting"
    """
    folders = list(Path(data_dir).glob("*/"))
    sorted_folders = sorted(folders, key=lambda x: _natural_sort_key(x.stem))

    image_patterns = ["*.jpg", "*.JPG", "*.jpeg", "*.JPEG"]
    pdf_patterns = ["*.pdf", "*.PDF"]
    for f in sorted_folders:
        images = []
        pdfs = []
        for p in image_patterns:
            images.extend(Path(data_dir / f).glob(p))
        for p in pdf_patterns:
            pdfs.extend(Path(data_dir / f).glob(p))
        sorted_images = sorted(images, key=lambda x: _natural_sort_key(x.stem))
        sorted_pdfs = sorted(pdfs, key=lambda x: _natural_sort_key(x.stem))
        assert len(sorted_images) == 0 or len(sorted_pdfs) == 0

        for pg, pdf_im, pdf_file in _notebook_images(sorted_pdfs):
            raw_img = Image.open(io.BytesIO(pdf_im.data))
            img = _process_image(raw_img)
            blob = _image_to_blob(img)
            d = BaroqueInputImage(
                page=pg,
                filename=pdf_file.name,
                folder=f.name,
                image=blob,
                width=img.width,
                height=img.height,
                original_width=raw_img.width,
                original_height=raw_img.height,
            )
            yield d

        for i, img_path in enumerate(sorted_images):
            raw_img = Image.open(img_path)
            img = _process_image(raw_img)
            blob = _image_to_blob(img)
            d = BaroqueInputImage(
                page=(i + 1),
                filename=img_path.name,
                folder=f.name,
                image=blob,
                width=img.width,
                height=img.height,
                original_width=raw_img.width,
                original_height=raw_img.height,
            )
            yield d


def _natural_sort_key(s: str) -> list:
    """
    Create a key for natural sorting of strings containing numbers.
    Example: "part 2" -> ["part ", 2]
    """

    def convert(text):
        return int(text) if text.isdigit() else text.lower()

    return [convert(c) for c in re.split("([0-9]+)", s)]


def _process_image(img):
    # Apply scaling if needed
    max_dim = max(img.width, img.height)
    scale = cfg.longside_res / max_dim
    if scale < 1.0:
        new_size = (int(img.width * scale), int(img.height * scale))
        scaled_img = img.resize(new_size, Image.Resampling.LANCZOS)
    else:
        scaled_img = img
    # convert to greyscale
    result = scaled_img.convert("L")
    return result


def _image_to_blob(pil_image: Image.Image, quality: int = 95) -> bytes:
    """Convert PIL Image to JPEG bytes for database storage"""
    buffer = io.BytesIO()
    pil_image.save(buffer, format="JPEG", quality=quality)
    return buffer.getvalue()
