"""
Commande Django pour envoyer les rappels d'expiration de concession.
À exécuter quotidiennement via un Cron Job sur Render.
Usage: python manage.py send_expiration_reminders
"""
import os
import requests
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.core.models import Concession, RappelExpiration


class Command(BaseCommand):
    help = 'Envoie les emails de rappel d\'expiration des concessions (J-30, J-15, J-7, J-0)'

    def handle(self, *args, **kwargs):
        self.stdout.write("🚀 Démarrage de la vérification des expirations de concessions...")
        
        today = timezone.now().date()
        brevo_api_key = os.environ.get('BREVO_API_KEY')
        
        if not brevo_api_key:
            self.stdout.write(self.style.ERROR("❌ BREVO_API_KEY non trouvée dans les variables d'environnement."))
            return

        # Définition des délais à vérifier (jours, type de rappel, sujet de l'email)
        delais = [
            (30, RappelExpiration.TypeRappel.J30, "Votre concession arrive à expiration dans 30 jours"),
            (15, RappelExpiration.TypeRappel.J15, "Rappel : Votre concession expire dans 15 jours"),
            (7, RappelExpiration.TypeRappel.J7, "URGENT : Votre concession expire dans 7 jours"),
            (0, RappelExpiration.TypeRappel.J0, "ALERTE : Votre concession a expiré aujourd'hui"),
        ]

        total_envoyes = 0
        total_echecs = 0

        for jours, type_rappel, sujet in delais:
            date_cible = today + timedelta(days=jours)
            
            # Trouver les concessions actives qui expirent exactement à cette date
            concessions_a_rappeler = Concession.objects.filter(
                date_fin=date_cible,
                statut=Concession.StatutConcession.ACTIVE
            ).select_related('concessionnaire', 'caveau')

            for concession in concessions_a_rappeler:
                # Vérifier si ce rappel a déjà été envoyé pour cette concession (évite le spam)
                if RappelExpiration.objects.filter(concession=concession, type_rappel=type_rappel).exists():
                    continue

                client = concession.concessionnaire
                if not client or not client.email:
                    self.stdout.write(self.style.WARNING(f"⚠️ Pas d'email pour la concession {concession.numero_contrat}"))
                    continue

                # Préparation du payload pour l'API Brevo
                email_data = {
                    "sender": {
                        "name": "Gestion Cimetière", 
                        "email": os.environ.get('ADMIN_EMAIL', 'no-reply@cimetiere.com')
                    },
                    "to": [{"email": client.email, "name": client.get_full_name()}],
                    "subject": f"[{sujet}] - Concession N° {concession.numero_contrat}",
                    "htmlContent": f"""
                    <h2>Bonjour {client.get_full_name()},</h2>
                    <p>Nous vous informons que la concession <strong>N° {concession.numero_contrat}</strong> 
                    située au caveau <strong>{concession.caveau.code}</strong> {sujet.lower()} (Date de fin : {concession.date_fin.strftime('%d/%m/%Y')}).</p>
                    <p>Nous vous invitons à vous rapprocher du secrétariat pour procéder au renouvellement ou à la libération de l'emplacement.</p>
                    <p>Cordialement,<br>L'équipe de gestion du cimetière.</p>
                    """
                }

                try:
                    # Envoi via l'API Brevo
                    response = requests.post(
                        "https://api.brevo.com/v3/smtp/email",
                        json=email_data,
                        headers={
                            "accept": "application/json",
                            "api-key": brevo_api_key,
                            "content-type": "application/json"
                        },
                        timeout=10
                    )
                    
                    if response.status_code in [200, 201]:
                        # Enregistrer le succès dans l'historique
                        RappelExpiration.objects.create(
                            concession=concession,
                            type_rappel=type_rappel,
                            statut_envoi=RappelExpiration.StatutEnvoi.SUCCES
                        )
                        total_envoyes += 1
                        self.stdout.write(self.style.SUCCESS(f"✅ Rappel {type_rappel} envoyé à {client.email} pour {concession.numero_contrat}"))
                        
                        # Si c'est le Jour J, on passe automatiquement le statut de la concession à EXPIREE
                        if jours == 0:
                            concession.statut = Concession.StatutConcession.EXPIREE
                            concession.save(update_fields=['statut'])
                            self.stdout.write(self.style.WARNING(f"🔒 Concession {concession.numero_contrat} passée en statut EXPIREE"))
                    else:
                        raise Exception(f"Brevo API Error: {response.status_code} - {response.text}")
                        
                except Exception as e:
                    # Enregistrer l'échec dans l'historique
                    RappelExpiration.objects.create(
                        concession=concession,
                        type_rappel=type_rappel,
                        statut_envoi=RappelExpiration.StatutEnvoi.ECHEC,
                        message_erreur=str(e)
                    )
                    total_echecs += 1
                    self.stdout.write(self.style.ERROR(f"❌ Échec envoi à {client.email} : {str(e)}"))

        self.stdout.write(self.style.SUCCESS(f"\n🎉 Traitement terminé ! Succès: {total_envoyes}, Échecs: {total_echecs}"))