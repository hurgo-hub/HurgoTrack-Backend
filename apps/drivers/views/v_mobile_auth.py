"""Login de la app del conductor: tokens en el cuerpo (no cookies) y sesión larga.

- ``POST /api/mobile/auth/token/`` {username, password} -> {access, refresh, driver}
- ``POST /api/mobile/auth/refresh/`` {refresh} -> {access, refresh} (rota el refresh)
Solo conductores activos (permiso ``trips.drive_trip`` y registro de conductor activo). La app manda
``Authorization: Bearer <access>`` a los mismos workflows que la web.
"""

from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

NOT_A_DRIVER = "Esta app es para conductores de Hurgo."


def active_driver(user):
    from apps.drivers.models import M_driver

    if user is None or not user.is_active or not user.has_perm("trips.drive_trip"):
        return None
    return M_driver.objects.filter(user_id=user, is_active=True).first()


def _tokens(user):
    refresh = RefreshToken.for_user(user)
    refresh.set_exp(lifetime=timedelta(days=settings.MOBILE_REFRESH_DAYS))
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


class Sz_login_in(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=128)


class Sz_refresh_in(serializers.Serializer):
    refresh = serializers.CharField()


class MobileTokenView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "mobile_login"

    def post(self, request):
        data = Sz_login_in(data=request.data)
        data.is_valid(raise_exception=True)
        user = authenticate(request, username=data.validated_data["username"].strip(),
                            password=data.validated_data["password"])
        if user is None:
            return Response({"detail": "Usuario o contraseña incorrectos."}, status=status.HTTP_401_UNAUTHORIZED)
        driver = active_driver(user)
        if driver is None:
            return Response({"detail": NOT_A_DRIVER}, status=status.HTTP_403_FORBIDDEN)
        return Response({**_tokens(user), "driver": {
            "id": driver.pk, "username": user.username, "name": str(driver),
            "license_category": driver.license_category,
        }})


class MobileRefreshView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        data = Sz_refresh_in(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            old = RefreshToken(data.validated_data["refresh"])
            user = get_user_model().objects.filter(pk=old["user_id"]).first()
            old.blacklist()  # cada refresh se usa una sola vez
        except TokenError:
            return Response({"detail": "La sesión venció. Vuelve a ingresar."}, status=status.HTTP_401_UNAUTHORIZED)
        if active_driver(user) is None:
            return Response({"detail": NOT_A_DRIVER}, status=status.HTTP_403_FORBIDDEN)
        return Response(_tokens(user))
