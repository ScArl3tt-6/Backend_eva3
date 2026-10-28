# ============================================================
# usuarios/serializers.py — TOKEN JWT CON EL CLAIM "rol"
# El rol va dentro del token firmado para que los permisos de la
# API (usuarios/permisos.py) puedan leerlo sin otra consulta a la
# base de datos, y para que, si el rol guardado cambia, el token
# antiguo deje de coincidir con la base en la siguiente verificación.
# ============================================================
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class TokenObtenerParSerializer(TokenObtainPairSerializer):
    """Login JWT: además de access/refresh, el access lleva el claim "rol"."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["rol"] = user.rol
        token["nombre_completo"] = user.nombre_completo
        return token
