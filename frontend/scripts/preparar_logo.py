"""Genera versiones web del logo a partir de marca/logo-original.png (fondo blanco -> transparente).

Uso: python scripts/preparar_logo.py   (desde la carpeta frontend; requiere Pillow)
"""
from pathlib import Path

from PIL import Image

PUBLIC = Path(__file__).resolve().parents[1] / "public"


def sin_fondo(im: Image.Image) -> Image.Image:
    """Vuelve transparente el blanco del fondo, con borde suave para no dejar halo."""
    im = im.convert("RGBA")
    datos = []
    for r, g, b, a in im.getdata():
        claridad = min(r, g, b)
        if claridad >= 248:
            datos.append((r, g, b, 0))
        elif claridad >= 225:
            datos.append((r, g, b, int(a * (248 - claridad) / 23)))
        else:
            datos.append((r, g, b, a))
    im.putdata(datos)
    return im


def recortar(im: Image.Image, caja, alto=None, ancho=None) -> Image.Image:
    parte = im.crop(caja)
    parte = parte.crop(parte.getbbox())
    if alto:
        parte = parte.resize((round(parte.width * alto / parte.height), alto), Image.LANCZOS)
    if ancho:
        parte = parte.resize((ancho, round(parte.height * ancho / parte.width)), Image.LANCZOS)
    return parte


def main():
    logo = sin_fondo(Image.open(Path(__file__).resolve().parents[1] / "marca" / "logo-original.png"))
    recortar(logo, (300, 90, 1060, 775), alto=160).save(PUBLIC / "marca.png", optimize=True)
    recortar(logo, (100, 799, 1155, 965), alto=96).save(PUBLIC / "marca-texto.png", optimize=True)
    recortar(logo, (90, 80, 1165, 1135), ancho=720).save(PUBLIC / "logo-web.webp", quality=88, method=6)
    icono = recortar(logo, (300, 90, 1060, 775), alto=64)
    lienzo = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    lienzo.paste(icono, ((64 - icono.width) // 2, 0), icono)
    lienzo.save(PUBLIC / "favicon.png", optimize=True)
    print("Generados: marca.png, marca-texto.png, logo-web.webp, favicon.png")


if __name__ == "__main__":
    main()
