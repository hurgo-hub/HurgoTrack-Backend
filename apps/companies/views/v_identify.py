"""Paso 1 del login: identificar al usuario antes de pedir la contraseña.

Respuesta NEUTRA: no dice si el usuario existe ni si está activo (así no sirve para averiguar
qué cuentas hay). Solo devuelve la marca de su empresa cuando el usuario existe, está activo y
pertenece a una sola empresa activa; en cualquier otro caso, ``company: null``.
Límite de consultas por cliente: ``DEFAULT_THROTTLE_RATES["auth_identify"]``.
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers
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
        company = None
        user = get_user_model().objects.filter(username__iexact=username, is_active=True).first()
        if user is not None:
            links = list(
                M_user_company.objects.filter(user_id=user, is_active=True, company_id__is_active=True)
                .select_related("company_id")[:2]
            )
            if len(links) == 1:
                c = links[0].company_id
                company = {"name": c.name, "color": c.color or None, "slogan": c.slogan or None}
        return Response({"company": company})
