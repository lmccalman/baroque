from dataclasses import dataclass


@dataclass
class BaroqueInputImage:

    page: int
    filename: str
    folder: str
    image: bytes
    width: int
    height: int
    original_width: int
    original_height: int


@dataclass
class BaroquePage:
    input_image: BaroqueInputImage
    english_text: str
    french_text: str
    english_latex: str
    french_latex: str


# BaroqueInputImage = namedtuple(
#     "BaroqueInputImage",
#     [
#         "page",
#         "filename",
#         "folder",
#         "image",
#         "width",
#         "height",
#         "original_width",
#         "original_height",
#     ],
# )
