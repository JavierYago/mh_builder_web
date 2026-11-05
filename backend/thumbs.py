"""Miniaturas bajo demanda para imágenes remotas muy pesadas (renders 4K de World en Kiranico).

La primera vez que se pide una imagen se descarga, se recorta al arma (detectando lo que
destaca sobre el fondo) y se guarda como WebP de 256 px en IMAGES_DIR/thumbs. Solo se aceptan
URLs de una lista blanca para evitar que el endpoint sirva de proxy abierto (SSRF).
"""
import hashlib
import io
import re
import threading

import requests
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageOps

from . import config

ALLOWED = re.compile(r"^https://cdn\.kiranico\.net/file/kiranico/mhworld-web/images/wp/factory/[a-z]{2,5}/[A-Za-z0-9]{4,16}\.jpg$")
SIZE = 256
_locks: dict[str, threading.Lock] = {}
_guard = threading.Lock()


def allowed(url: str) -> bool:
    return bool(ALLOWED.match(url or ""))


def _cutout(im: Image.Image) -> Image.Image:
    """Separa el arma del fondo degradado: máscara = lo que destaca sobre el fondo difuminado."""
    small = im.convert("L").resize((480, 270))
    background = small.filter(ImageFilter.GaussianBlur(40))
    mask = ImageChops.subtract(small, background).point(lambda v: 255 if v > 16 else 0)
    mask = mask.filter(ImageFilter.MaxFilter(5))
    ImageDraw.Draw(mask).rectangle((0, int(270 * 0.9), 480, 270), fill=0)  # marca de agua
    mask = mask.resize(im.size, Image.BILINEAR).filter(ImageFilter.GaussianBlur(3))
    rgba = im.convert("RGBA")
    rgba.putalpha(mask)
    box = mask.point(lambda v: 255 if v > 40 else 0).getbbox()
    if box:
        rgba = rgba.crop(box)
    side = int(max(rgba.size) * 1.08)
    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    square.paste(rgba, ((side - rgba.width) // 2, (side - rgba.height) // 2))
    return square


def get(url: str) -> bytes:
    key = hashlib.sha1(url.encode()).hexdigest()
    path = config.IMAGES_DIR / "thumbs" / f"{key}.webp"
    if path.exists():
        return path.read_bytes()
    with _guard:
        lock = _locks.setdefault(key, threading.Lock())
    with lock:
        if path.exists():
            return path.read_bytes()
        resp = requests.get(url, timeout=60, headers={"User-Agent": config.USER_AGENT})
        resp.raise_for_status()
        im = Image.open(io.BytesIO(resp.content)).convert("RGB")
        im = _cutout(im)
        im.thumbnail((SIZE, SIZE), Image.LANCZOS)
        rgb = ImageEnhance.Brightness(ImageOps.autocontrast(im.convert("RGB"), cutoff=0.5)).enhance(1.3)
        rgb.putalpha(im.getchannel("A"))
        im = rgb
        out = io.BytesIO()
        im.save(out, "WEBP", quality=82)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(out.getvalue())
        return out.getvalue()
