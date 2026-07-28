"""
Middleware utilitaires pour l'application core.
"""
import threading

_thread_locals = threading.local()


def get_current_user():
    """Retourne l'utilisateur associé à la requête HTTP en cours (ou None)."""
    return getattr(_thread_locals, 'user', None)


class CurrentUserMiddleware:
    """
    Rend l'utilisateur de la requête HTTP courante accessible en dehors du
    cycle requête/réponse (ex: depuis un logging.Handler), via une variable
    thread-local.

    Utilisé par apps.core.logging_handlers.DatabaseAuditHandler afin que
    chaque entrée du journal d'audit (CDC section 4) puisse être rattachée
    à l'utilisateur authentifié qui a déclenché l'action, sans avoir à
    modifier les dizaines d'appels `logger.info(...)` déjà présents dans
    le projet.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.user = getattr(request, 'user', None)
        try:
            response = self.get_response(request)
        finally:
            _thread_locals.user = None
        return response
