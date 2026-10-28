# ============================================================
# accesos/qr.py — GENERACIÓN DEL CÓDIGO QR DEL SOCIO
# Se genera en SVG (vectorial) con la librería "qrcode" usando su
# fábrica de imágenes SvgPathImage, que NO depende de Pillow.
#
# El QR codifica únicamente el token UUID del socio: nunca su
# nombre, RUT ni ningún otro dato personal (criterio de seguridad
# de la pauta).
# ============================================================

import io

import qrcode
import qrcode.image.svg


def generar_qr_svg(token) -> bytes:
    """Devuelve el SVG (bytes) del código QR que representa el token recibido."""
    imagen = qrcode.make(str(token), image_factory=qrcode.image.svg.SvgPathImage, box_size=10)
    buffer = io.BytesIO()
    imagen.save(buffer)
    return buffer.getvalue()
