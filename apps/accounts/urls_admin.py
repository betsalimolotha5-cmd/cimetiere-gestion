"""
URLs pour les API Admin de l'application accounts.
"""
from django.urls import path
from .api_admin import router as accounts_admin_router

urlpatterns = [
    path('admin/', accounts_admin_router.urls),
]
