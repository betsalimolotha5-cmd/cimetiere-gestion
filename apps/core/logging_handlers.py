"""
Handler de logging pour la journalisation immuable exigée par le CDC
(section 4 : "Audit Trail : Journalisation immuable de qui a modifié le
statut d'un caveau, à quelle date et heure").

Ce handler s'attache au logger 'audit' déjà utilisé dans tout le projet
(apps/core, apps/billing, apps/accounts, apps/portal, apps/notifications,
apps/reports — cf. `logging.getLogger('audit')`) et persiste chaque
enregistrement dans la table AuditLogEntry, sans nécessiter la moindre
modification des dizaines de points d'appel existants.
"""
import logging


class DatabaseAuditHandler(logging.Handler):
    """Persiste les logs du logger 'audit' dans la table AuditLogEntry."""

    def emit(self, record):
        # Import tardif : au chargement de LOGGING (settings.py), les
        # modèles Django ne sont pas encore prêts (apps registry).
        try:
            from django.apps import apps
            if not apps.ready:
                return

            from apps.core.models import AuditLogEntry
            from apps.core.middleware import get_current_user

            user = get_current_user()
            if user is not None and not getattr(user, 'is_authenticated', False):
                user = None

            AuditLogEntry.objects.create(
                niveau=record.levelname if record.levelname in ('INFO', 'WARNING', 'ERROR') else 'INFO',
                utilisateur=user,
                action=self._extract_action(record.getMessage()),
                module=record.module,
                message=record.getMessage(),
            )
        except Exception:
            # Un incident sur le journal d'audit ne doit JAMAIS faire
            # échouer l'action métier en cours (ex: une réservation ne doit
            # pas planter parce que l'écriture d'audit échoue).
            self.handleError(record)

    @staticmethod
    def _extract_action(message: str) -> str:
        """Extrait le code d'action au début du message, ex: 'CAVEAU_RESERVED: code=...' -> 'CAVEAU_RESERVED'."""
        if ':' in message:
            candidate = message.split(':', 1)[0].strip()
            if candidate and ' ' not in candidate:
                return candidate[:100]
        return message[:100]
