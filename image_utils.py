import io

from PIL import Image


def to_sticker_png(raw: bytes) -> bytes:
    """Resize so one side is exactly 512px, keeping aspect, return PNG bytes.

    Telegram requires static sticker images to be PNG/WEBP with one side
    exactly 512px and the other <= 512px.
    """
    img = Image.open(io.BytesIO(raw)).convert("RGBA")
    w, h = img.size
    if w >= h:
        new_w = 512
        new_h = max(1, round(h * 512 / w))
    else:
        new_h = 512
        new_w = max(1, round(w * 512 / h))
    img = img.resize((new_w, new_h), Image.LANCZOS)
    out = io.BytesIO()
    img.save(out, format="PNG", optimize=True)
    return out.getvalue()
