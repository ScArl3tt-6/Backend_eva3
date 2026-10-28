# ============================================================
# usuarios/views.py — LOGIN JWT (API)
# ============================================================
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import TokenObtenerParSerializer


class TokenObtenerParView(TokenObtainPairView):
    """POST /api/auth/token/: devuelve access y refresh; el access incluye el claim "rol"."""

    serializer_class = TokenObtenerParSerializer
