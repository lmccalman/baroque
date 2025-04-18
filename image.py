from PIL import Image
import io
from pathlib import Path

def save_page_image(image_file_object, page_num: int, output_dir: Path, scale: float = 1.0):
    # Create filename: page_number.jpg
    img_filename = f"page_{page_num:04d}.jpg"
    img_path = output_dir / img_filename

    # Load image data into PIL Image
    img = Image.open(io.BytesIO(image_file_object.data))

    original_size = (img.width, img.height)
    # Apply scaling if needed
    if scale < 1.0:
        new_size = (int(img.width * scale), int(img.height * scale))
        img = img.resize(new_size, Image.Resampling.LANCZOS)

    # convert to greyscale
    img = img.convert("L")

    # Save the image
    img.save(img_path, "JPEG", quality=95)
    print(f"Saved image: {img_path.stem} (scaled: {original_size[0]}x{original_size[1]} -> {img.width}x{img.height})")

