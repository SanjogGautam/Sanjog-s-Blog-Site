import uuid
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageOps

PROFILE_PIC_DIR = Path("media/profile_pics")  # ← no leading slash, relative to project root

def process_profile_image(content: bytes) -> str:
    # 1. Open the raw bytes as an image
    with Image.open(BytesIO(content)) as img:#it will if the bytes are not real image

        # 2. Fix rotations from phone cameras (EXIF orientation data)
        img = ImageOps.exif_transpose(img)

        # 3. Convert anything (PNG, WEBP, RGBA) to plain RGB for JPEG saving
        if img.mode != "RGB":
            img = img.convert("RGB")

        # 4. Crop to a square from the center, then resize to 256×256
        img = ImageOps.fit(img, (256, 256), method=Image.LANCZOS)

        # 5. Generate a unique filename so uploads never overwrite each other
        filename = f"{uuid.uuid4().hex}.jpg"
        filepath=(PROFILE_PIC_DIR / filename)

        # 6. Make sure the folder exists (creates it if it doesn't)
        PROFILE_PIC_DIR.mkdir(parents=True, exist_ok=True)

        # 7. Save the processed image to disk
        img.save(filepath, format="JPEG", quality=85, optimize=True)

    return filename  # e.g. "a3f9c12d...jpg" — stored in DB, served via /media/profile_pics/
#delete profile_picture function
def delete_profile_image(filename:str|None)->None:
    if filename is None:
        return 
    filepath=PROFILE_PIC_DIR/filename
    if filepath.exists():
        filepath.unlink()