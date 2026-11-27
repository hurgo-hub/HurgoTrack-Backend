"""Paso 1 del login: identificar al usuario antes de pedir la contraseña.

Valida contra la base que el usuario exista y esté activo; si no, responde 404 (no existe) o 403
(desactivado) y el login no pasa a la contraseña. Si existe, devuelve la marca de su empresa cuando
pertenece a una sola empresa activa (``company``; ``null`` para Hurgo o varias empresas).
Para que no sirva para probar usuarios en masa, hay límite de consultas por cliente:
``DEFAULT_THROTTLE_RATES["auth_identify"]`` (AUTH_IDENTIFY_RATE en el .env).
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from enginedj.base.models import M_user_company


class Sz_identify_in(serializers.Serializer):
    username = serializers.CharField(max_length=150)


class IdentifyUserView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_identify"

    def post(self, request):
        data = Sz_identify_in(data=request.data)
        data.is_valid(raise_exception=True)
        username = data.validated_data["username"].strip()
        user = get_user_model().objects.filter(username__iexact=username).first()
        if user is None:
            return Response({"detail": "El usuario no existe.", "code": "user_not_found"},
                            status=status.HTTP_404_NOT_FOUND)
        if not user.is_active:
            return Response({"detail": "El usuario está desactivado. Habla con el administrador.",
                             "code": "user_inactive"}, status=status.HTTP_403_FORBIDDEN)
        company = None
        links = list(
            M_user_company.objects.filter(user_id=user, is_active=True, company_id__is_active=True)
            .select_related("company_id")[:2]
        )
        if len(links) == 1:
            c = links[0].company_id
            company = {"name": c.name, "color": c.color or None, "slogan": c.slogan or None}
        return Response({"username": user.username, "company": company})
