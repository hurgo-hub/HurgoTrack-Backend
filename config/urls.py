from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.companies.views.v_identify import IdentifyUserView
from apps.drivers.views.v_mobile_auth import MobileRefreshView, MobileTokenView

urlpatterns = [
    path("admin/", admin.site.urls),
    # Motor: auth por cookies (api/auth/token/, token/refresh/, logout/) y workflows.
    # Las apps de Hurgo exponen sus acciones como workflows:
    #   POST /api/workflows/sync/<nombre>/  (el seeds.py de cada app; python manage.py seed_workflows)
    # Paso 1 del login (respuesta neutra, con límite de consultas): marca de la empresa del usuario
    path("api/auth/identify/", IdentifyUserView.as_view()),
    # App del conductor: tokens en el cuerpo (Authorization: Bearer), sesión larga
    path("api/mobile/auth/token/", MobileTokenView.as_view()),
    path("api/mobile/auth/refresh/", MobileRefreshView.as_view()),
    path("api/", include("enginedj.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
