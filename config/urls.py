"""
Configuration des URLs du projet Gestion Cimetière.
Conforme au CDC : toutes les routes, API REST, documentation.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from django.shortcuts import redirect
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView


def redirect_to_admin(request):
    """Redirige la racine vers l'admin."""
    return redirect('/admin/')


# Handlers d'erreur personnalisés
handler400 = 'django.views.defaults.bad_request'
handler403 = 'django.views.defaults.permission_denied'
handler404 = 'django.views.defaults.page_not_found'
handler500 = 'django.views.defaults.server_error'


urlpatterns = [
    # Page d'accueil - redirige vers l'admin
    path('', redirect_to_admin, name='accueil'),

    path('init-db/', core_views.init_db, name='init_db'),
    
    # Administration Django
    path('admin/', admin.site.urls),
    
    # Portail client public
    path('portal/', include('apps.portal.urls')),
    
    # Gestion du cimetière (zones, caveaux, concessions, etc.)
    path('cimetiere/', include('apps.core.urls')),
    
    # Gestion des comptes utilisateurs
    path('accounts/', include('apps.accounts.urls')),
    
    # Authentification à double facteur
    path('mfa/', include('apps.mfa.urls')),
    
    # Facturation et paiements
    path('billing/', include('apps.billing.urls')),
    
    # Rapports et statistiques
    path('rapports/', include('apps.reports.urls')),

    path('init-db/', core_views.init_db, name='init_db'),
    
    # API REST
    path('api/v1/', include('apps.core.api_urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# Servir les fichiers médias en développement
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
else:
    # En production, servir les fichiers media manuellement
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]