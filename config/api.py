"""
Configuration de l'API Django Ninja.
"""
from ninja import NinjaAPI
from ninja.security import HttpBearer
from django.conf import settings

# Import des routers des différentes apps
from apps.accounts.views import router as accounts_router
from apps.core.views import router as core_router
from apps.core.import_export_views import router as import_export_router
from apps.billing.views import router as billing_router
from apps.notifications.views import router as notifications_router
from apps.reports.views import router as reports_router


class AuthBearer(HttpBearer):
    """Authentification par token Bearer."""
    
    def authenticate(self, request, token):
        from apps.accounts.services import TokenService
        user = TokenService.verify_token(token)
        if user:
            return token
        return None


# Création de l'API
api = NinjaAPI(
    title="API Gestion Cimetière",
    version="1.0.0",
    description="API REST pour la gestion numérique des cimetières",
    urls_namespace="api",
    docs_url="/docs/",
)

# Ajouter l'authentification
api.add_security(HttpBearer(), AuthBearer())

# Enregistrer les routers
api.add_router("/accounts/", accounts_router)
api.add_router("/core/", core_router)
api.add_router("/core/", import_export_router)  # Import/Export sous /core/
api.add_router("/billing/", billing_router)
api.add_router("/notifications/", notifications_router)
api.add_router("/reports/", reports_router)


# Gestion des erreurs
@api.exception_handler(Exception)
def custom_exception_handler(request, exc):
    return api.create_response(
        request,
        {"success": False, "message": str(exc)},
        status=500,
    )