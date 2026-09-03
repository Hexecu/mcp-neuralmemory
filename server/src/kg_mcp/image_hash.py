"""Perceptual hashes used to suppress duplicate screenshot events."""

import base64
from io import BytesIO

from PIL import Image


def dhash_from_base64(image_base64: str, hash_size: int = 8) -> str | None:
    """Compute a dHash for a base64-encoded image, or return None when invalid."""
    try:
        image_bytes = base64.b64decode(image_base64, validate=True)
        with Image.open(BytesIO(image_bytes)) as image:
            resized = image.convert("L").resize((hash_size + 1, hash_size))
            if hasattr(resized, "get_flattened_data"):
                pixels = list(resized.get_flattened_data())
            else:  # Pillow < 12
                pixels = list(resized.getdata())
    except Exception:
        return None

    difference = []
    for row in range(hash_size):
        row_start = row * (hash_size + 1)
        for column in range(hash_size):
            difference.append(pixels[row_start + column] > pixels[row_start + column + 1])

    output = []
    byte = 0
    for index, value in enumerate(difference):
        if value:
            byte |= 1 << (index % 8)
        if index % 8 == 7:
            output.append(f"{byte:02x}")
            byte = 0
    return "".join(output)


def hamming_distance(hash_a: str, hash_b: str) -> int:
    """Compute Hamming distance between two hex-encoded hashes."""
    if not hash_a or not hash_b:
        return 64
    try:
        return (int(hash_a, 16) ^ int(hash_b, 16)).bit_count()
    except ValueError:
        return 64
