# ============================================================
# socios/validadores.py — VALIDACIÓN DEL RUT CHILENO
# Responsabilidad: calcular y verificar el dígito verificador (DV)
# con el algoritmo módulo 11 y normalizar el formato de guardado
# ("12345678-5", sin puntos) para que la unicidad del campo compare
# siempre lo mismo sin importar cómo lo haya escrito la persona.
# ============================================================

from django.core.exceptions import ValidationError


def limpiar_rut(rut: str) -> str:
    """Quita puntos, guiones y espacios; deja el DV en mayúscula."""
    return rut.upper().replace(".", "").replace("-", "").replace(" ", "").strip()


def calcular_dv(cuerpo: str) -> str:
    """Dígito verificador módulo 11 del cuerpo numérico del RUT."""
    suma = 0
    multiplicador = 2
    for digito in reversed(cuerpo):
        suma += int(digito) * multiplicador
        multiplicador = multiplicador + 1 if multiplicador < 7 else 2
    resto = 11 - (suma % 11)
    if resto == 11:
        return "0"
    if resto == 10:
        return "K"
    return str(resto)


def formatear_rut(rut: str) -> str:
    """Devuelve el RUT en formato canónico "cuerpo-DV", sin puntos."""
    limpio = limpiar_rut(rut)
    return f"{limpio[:-1]}-{limpio[-1]}"


def validar_rut(value: str) -> None:
    """Validador de campo: rechaza un RUT mal formado o con DV incorrecto."""
    limpio = limpiar_rut(value)

    if len(limpio) < 2:
        raise ValidationError("El RUT es demasiado corto.")

    cuerpo, dv = limpio[:-1], limpio[-1]

    if not cuerpo.isdigit():
        raise ValidationError("El RUT debe tener solo números antes del dígito verificador.")

    if not (7 <= len(cuerpo) <= 8):
        raise ValidationError("El RUT debe tener entre 7 y 8 dígitos antes del verificador.")

    if calcular_dv(cuerpo) != dv:
        raise ValidationError("El RUT ingresado no es válido: el dígito verificador no coincide.")
