from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # Motor: auth por cookies (api/auth/token/, token/refresh/, logout/) y workflows.
    # Las apps de Hurgo exponen sus acciones como workflows:
    #   POST /api/workflows/sync/<nombre>/  (el seeds.py de cada app; python manage.py seed_workflows)
    path("api/", include("enginedj.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
