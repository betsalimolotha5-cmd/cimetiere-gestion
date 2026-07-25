"""
Configuration des URLs du projet Gestion Cimetière.
Conforme CDC : Intégration MFA avec redirection automatique.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from django.shortcuts import redirect
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

from apps.core import views as core_views


def redirect_to_portal(request):
    """Redirige la racine vers la page de connexion."""
    return redirect('/mfa/login/')


def redirect_login_to_mfa(request):
    """Redirige /accounts/login/ vers /mfa/login/ pour utiliser le MFA."""
    return redirect('/mfa/login/')


handler400 = 'django.views.defaults.bad_request'
handler403 = 'django.views.defaults.permission_denied'
handler404 = 'django.views.defaults.page_not_found'
handler500 = 'django.views.defaults.server_error'


urlpatterns = [
    path('', redirect_to_portal, name='accueil'),
    
    # Page d'initialisation de la base (temporaire, pour créer les tables et le superuser)
    path('init-db/', core_views.init_db, name='init_db'),
    
    path('admin/', admin.site.urls),
    
    # ✨ MFA : Doit être AVANT accounts pour prioriser les vues MFA
    path('mfa/', include('apps.mfa.urls')),
    
    # Accounts : Redirige login vers MFA
    path('accounts/login/', redirect_login_to_mfa, name='accounts_login_redirect'),
    path('accounts/', include('apps.accounts.urls')),
    
    # API Admin (pour le frontend Flet)
    path('api/v1/accounts/', include('apps.accounts.urls_admin')),
    path('api/v1/billing/', include('apps.billing.urls_admin')),
    path('api/v1/portal/', include('apps.portal.urls_admin')),
    
    path('portal/', include('apps.portal.urls')),
    path('cimetiere/', include('apps.core.urls')),
    path('billing/', include('apps.billing.urls')),
    path('rapports/', include('apps.reports.urls')),
    path('api/v1/', include('apps.core.api_urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
else:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]
