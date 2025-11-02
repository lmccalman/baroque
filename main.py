# import fnmatch
import io
import os
import shelve
import shutil
import signal
from logging import shutdown

# import sys
from pathlib import Path
from pydoc import plain
from unittest import skip
from urllib.parse import quote

import click
from anthropic import Anthropic
from PIL import Image

from base import BaroquePage
from dataimport import all_files, import_raw_files
from process import extract_text, format_text, translate_text

# from database import BaroqueDB, populate_database_from_files
# from latex import create_latex_document
# from pdf import find_all_files, find_pdf_files, notebook_images
# from pypdf import PdfReader

# import config as cfg
# from image import blob_to_image, save_page_image
# from old.process import analyse_text, extract_text, format_text, translate_text

running = True


def signal_handler(_sig, _frame):
    global running
    print("graceful exit...")
    running = False


@click.group()
def main():
    """Process PDF files, extracting images and text."""
    pass


def _compute_or_cache(input_page, client, db):
    key = f"{input_page.folder}|{input_page.filename}|{input_page.page}"
    if key in db:
        page = db[key]
        print(f"Retrieving {key} from cache...")
    else:
        print(f"Processing {key}...")
        french_text, _ocr_log = extract_text(client, input_page.image)
        english_text, _translate_log = translate_text(client, french_text)
        # french_tex, _french_format_log = format_text(client, french_text)
        # english_tex, _english_format_log = format_text(client, english_text)
        english_tex = ""
        french_tex = ""
        page = BaroquePage(
            input_page, english_text, french_text, english_tex, french_tex
        )
    return page


@main.command()
def process():
    signal.signal(signal.SIGINT, signal_handler)
    input_dir = Path.cwd() / "input_data"
    output_dir = Path.cwd() / "raw-output"
    output_dir.mkdir(parents=True, exist_ok=True)

    override = False

    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    db_path = Path.cwd() / "baroque"
    with shelve.open(db_path) as db:
        for input_page in all_files(input_dir):
            text_folder = output_dir / input_page.folder
            english_path = text_folder / f"english_page_{input_page.page:03d}.txt"
            french_path = text_folder / f"french_page_{input_page.page:03d}.txt"
            image_folder = text_folder / "images"
            image_path = image_folder / f"page_{input_page.page:03d}.jpg"

            if not os.path.isdir(text_folder):
                text_folder.mkdir(parents=True, exist_ok=False)
            if not os.path.isdir(image_folder):
                image_folder.mkdir(parents=True, exist_ok=False)

            # does the output already exist in filesystem?
            exists = (
                french_path.exists() and english_path.exists() and image_path.exists()
            )
            if exists and not override:
                key = f"{input_page.folder}|{input_page.filename}|{input_page.page}"
                print(f"skipping {key} as present in filesystem...")
                continue

            page = _compute_or_cache(input_page, client, db)

            # write french
            with open(french_path, "w", encoding="utf-8") as f:
                f.write(page.french_text)
                print(f"Written {french_path}")

            # write english
            with open(english_path, "w", encoding="utf-8") as f:
                f.write(page.english_text)
                print(f"Written {english_path}")

            # write image
            img = Image.open(io.BytesIO(page.input_image.image))
            img.save(image_path)
            print(f"Written {image_path}")


def folder_code(s):
    """Transforms the folder name to a simpler code"""
    result = s.replace(" ", "_").replace(".", "_").replace("-", "_")
    return result


def filter_txt(s):
    if "<output>" in s:
        print(f"WARNING: deleting {s}")
        return ""
    # s = s.replace("[", "(").replace("]", ")")

    # Characters that need escaping in Obsidian markdown
    # Order matters: backslash must be first to avoid double-escaping
    chars_to_escape = [
        "\\",
        "*",
        "_",
        "#",
        "`",
        "|",
        "~",
        "[",
        "]",
        "(",
        ")",
        "<",
        ">",
        "!",
        "+",
        "-",
        ".",
    ]
    result = s
    for char in chars_to_escape:
        result = result.replace(char, "\\" + char)

    # remove leading whitespace
    result = "\n".join(line.lstrip() for line in result.splitlines())

    return result


from pathlib import Path
from typing import List, Union

from PIL import Image


def rotate_image(in_path, out_path, rotation_angle=90):
    # Load the image
    img = Image.open(in_path)
    # Rotate (PIL rotates counter-clockwise, use negative for clockwise)
    rotated = img.rotate(-rotation_angle, expand=True)
    # Save back to the same path
    rotated.save(out_path)


ROTATE_LEFT_LIST = [
    "ADM_1_3935_1749",
    "ADM_1_3940_1754",
    "SP_84_527_1770_",
    "ADM_1_3942_1756",
    "ADM_1_3956_1769",
    "SP_78_279_1769",
    "SP_84_451_1748",
    "SP_84_506_1764",
    "SP_87_8_1742",
    "SP84_532_1771",
    "SP84_586_1756_64",
]
ROTATE_RIGHT_LIST = []


@main.command()
def obsidian():

    input_dir = Path.cwd() / "raw-output"
    output_dir = Path.cwd() / "baroque-vault"
    output_image_dir = output_dir / "images"
    output_reference_dir = output_dir / "reference"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_image_dir.mkdir(parents=True, exist_ok=True)
    output_reference_dir.mkdir(parents=True, exist_ok=True)

    # read in all input
    raw_data = import_raw_files(input_dir)
    for folder, files in raw_data.items():
        code = folder_code(folder)
        print(code)
        pages = []
        text_dest = output_dir / f"{code}.md"

        for i, (fren, eng, im) in enumerate(files):
            im_dest = output_image_dir / f"{code}--{im.name}"
            ref_dest = output_reference_dir / f"{code}--{(i+1):03d}.md"

            if any(s in im_dest.name for s in ROTATE_LEFT_LIST):
                print(f"rotating {im_dest}")
                rotate_image(im, im_dest)
            else:
                # just copy the image itself
                shutil.copyfile(im, im_dest)

            with open(eng, "r", encoding="utf-8") as f:
                eng_txt = f.read()
            with open(fren, "r", encoding="utf-8") as f:
                fren_txt = f.read()

            # ref_string = f"![[images/{im_dest.name}|800]]\n\n```\n{fren_txt}\n```\n---\n```\n{eng_txt}\n```"

            ref_string = f"Scan | Transcription | Translation\n -- | -- | --\n ![[images/{im_dest.name}|500]] |```\n{fren_txt}\n``` | ```\n{eng_txt}\n```"

            with open(ref_dest, "w", encoding="utf-8") as f:
                f.write(ref_string)

            filtered_eng_txt = filter_txt(eng_txt)
            ref_url = quote(f"reference/{ref_dest.name}")

            title_string = f"## Page {(i+1)}\n"
            image_string = f"![[images/{im_dest.name}|400]]\n[Reference]({ref_url})\n"

            out_string = f"{title_string}{image_string}\n{filtered_eng_txt}"
            pages.append(out_string)

        out_string = "\n\n---\n\n".join(pages)
        with open(text_dest, "w", encoding="utf-8") as f:
            f.write(out_string)


# @main.command()
# def process():

#     client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
#     input_dir = Path.cwd() / "input_data"
#     for input_page in find_all_files(input_dir):
#         result_txt, log_txt = extract_text(client, input_page.image_data)


# @main.command()
# def extract():
#     """Extract images from a PDF file."""
#     with BaroqueDB() as db:
#         images = db.get_pages()
#         for id, folder_name, page_number, image_data in images:
#             # result = old_lookup(folder_name, page_number)
#             # if result is None:
#             # image = blob_to_image(image_data)
#             import IPython

#             IPython.embed()
#             import sys

#             sys.exit()


# @main.command()
# @click.option(
#     "--override", is_flag=True, help="Always extract text even if text file exists"
# )
# @click.option(
#     "--npages",
#     type=int,
#     help="Maximum number of pages to process",
# )
# @click.argument("notebook_name", type=str)
# def ocr(notebook_name: str, override: bool, npages: int):
#     """Perform OCR on images from a PDF file."""
#     input_dir = Path.cwd() / "output" / notebook_name / "images"
#     input_images = sorted(
#         list(input_dir.glob("*.jpg")), key=lambda x: int(x.stem.split("_")[1])
#     )
#     if len(input_images) == 0:
#         raise ValueError(f"No images found for {notebook_name}")

#     # make the output directory if it doesn't exist
#     output_dir = Path.cwd() / "output" / notebook_name / "claude_ocr"
#     output_dir.mkdir(parents=True, exist_ok=True)

#     if npages is not None:
#         input_images = input_images[:npages]

#     for image_path in input_images:
#         print(f"Processing {image_path}")
#         text_path = output_dir / f"{image_path.stem}_french.txt"
#         latex_path = output_dir / f"{image_path.stem}_french.tex"
#         text_log_path = output_dir / f"{image_path.stem}_french.txt.log"
#         latex_log_path = output_dir / f"{image_path.stem}_french.tex.log"
#         if not text_path.exists() or override:
#             text, text_log = extract_text(image_path)
#             print(text_log)
#             latex, latex_log = format_text(text)
#             with open(text_path, "w") as f:
#                 f.write(text)
#             with open(latex_path, "w") as f:
#                 f.write(latex)
#             with open(text_log_path, "w") as f:
#                 f.write(text_log)
#             with open(latex_log_path, "w") as f:
#                 f.write(latex_log)
#         else:
#             print(f"Text file {text_path} exists, skipping")

#     # extract_images(pdf_path, override_text=override, max_pages=npages, model=model)


# @main.command()
# @click.option(
#     "--override", is_flag=True, help="Always extract text even if text file exists"
# )
# @click.option(
#     "--npages",
#     type=int,
#     help="Maximum number of pages to process",
# )
# @click.argument("notebook_name", type=str)
# def translate(notebook_name: str, npages: int, override: bool):
#     """Translate text from images in a PDF file."""

#     input_dir = Path.cwd() / "output" / notebook_name / "claude_ocr"
#     input_txt_files = sorted(
#         list(input_dir.glob("*.txt")), key=lambda x: int(x.stem.split("_")[1])
#     )
#     if len(input_txt_files) == 0:
#         raise ValueError(f"No OCR data found for {notebook_name}")

#     output_dir = Path.cwd() / "output" / notebook_name / "claude_ocr_claude_trans"
#     output_dir.mkdir(parents=True, exist_ok=True)
#     for input_txt_file in input_txt_files:
#         output_file = (
#             output_dir / f"{input_txt_file.stem.rstrip('_french')}_english.txt"
#         )
#         latex_file = output_dir / f"{input_txt_file.stem.rstrip('_french')}_english.tex"
#         text_log_file = (
#             output_dir / f"{input_txt_file.stem.rstrip('_french')}_english.txt.log"
#         )
#         latex_log_file = (
#             output_dir / f"{input_txt_file.stem.rstrip('_french')}_english.tex.log"
#         )
#         if not override and output_file.exists():
#             print(f"Skipping {output_file} because it exists")
#             continue
#         print(f"Translating {input_txt_file}")
#         text = input_txt_file.read_text()
#         translated_text, text_log = translate_text(text)
#         latex, latex_log = format_text(translated_text)
#         with open(output_file, "w") as f:
#             f.write(translated_text)
#         with open(latex_file, "w") as f:
#             f.write(latex)
#         with open(text_log_file, "w") as f:
#             f.write(text_log)
#         with open(latex_log_file, "w") as f:
#             f.write(latex_log)
#         print(f"{input_txt_file.stem} -> {output_file.stem}")


# @main.command()
# @click.argument("notebook_name", type=str)
# def collate(notebook_name: str):
#     """collate the OCR and translation text along with the original images to a pdf file compiled with latex"""

#     image_dir = Path.cwd() / "output" / notebook_name / "images"
#     french_dir = Path.cwd() / "output" / notebook_name / "claude_ocr"
#     english_dir = Path.cwd() / "output" / notebook_name / "claude_ocr_claude_trans"
#     image_files = sorted(
#         list(image_dir.glob("*.jpg")), key=lambda x: int(x.stem.split("_")[1])
#     )
#     french_files = sorted(
#         list(french_dir.glob("*.tex")), key=lambda x: int(x.stem.split("_")[1])
#     )
#     english_files = sorted(
#         list(english_dir.glob("*.tex")), key=lambda x: int(x.stem.split("_")[1])
#     )
#     plain_files = sorted(
#         list(english_dir.glob("*.txt")), key=lambda x: int(x.stem.split("_")[1])
#     )

#     image_keys = [int(f.stem.split("_")[1]) for f in image_files]
#     french_keys = [int(f.stem.split("_")[1]) for f in french_files]
#     english_keys = [int(f.stem.split("_")[1]) for f in english_files]
#     plain_keys = [int(f.stem.split("_")[1]) for f in plain_files]
#     pages = (
#         set(image_keys)
#         .intersection(french_keys)
#         .intersection(english_keys)
#         .intersection(plain_keys)
#     )
#     assert set(range(1, len(pages) + 1)) == set(
#         pages
#     ), "Page numbers are not contiguous"
#     print(f"Found {len(pages)} pages")

#     # filter the files to only include the pages that exist
#     image_files = [f for f in image_files if int(f.stem.split("_")[1]) in pages]
#     french_files = [f for f in french_files if int(f.stem.split("_")[1]) in pages]
#     english_files = [f for f in english_files if int(f.stem.split("_")[1]) in pages]
#     plain_files = [f for f in plain_files if int(f.stem.split("_")[1]) in pages]

#     # create the full summary
#     full_text = "\n\n".join([f.read_text() for f in plain_files])
#     summary, summary_log = analyse_text(full_text)

#     # zip the files together
#     latex_pages = list(zip(image_files, french_files, english_files))
#     output_dir = Path.cwd() / "output" / notebook_name
#     summary_log_file = output_dir / f"summary_{notebook_name}.log"
#     with open(summary_log_file, "w") as f:
#         f.write(summary_log)
#     create_latex_document(
#         latex_pages, output_dir / f"{notebook_name}.tex", notebook_name, summary
#     )


if __name__ == "__main__":
    main()
