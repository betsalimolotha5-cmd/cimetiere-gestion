"""
URLs pour les API Admin de l'application portal.
"""
from django.urls import path
from .api_admin import router as portal_admin_router

urlpatterns = [
    path('admin/', portal_admin_router.urls),
]
