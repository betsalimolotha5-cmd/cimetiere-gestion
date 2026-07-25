"""
URLs pour les API Admin de l'application billing.
"""
from django.urls import path
from .api_admin import router as billing_admin_router

urlpatterns = [
    path('admin/', billing_admin_router.urls),
]
