"""
Signaux Django pour automatiser les actions métier et assurer la cohérence des données.
"""
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
import logging

from .models import Concession, Caveau, DemandeExhumation, Inhumation

logger = logging.getLogger('audit')


@receiver(pre_save, sender=Concession)
def calculer_date_fin_concession(sender, instance, **kwargs):
    """Calcule automatiquement la date de fin pour les concessions temporaires."""
    if instance.type_concession == Concession.TypeConcession.TEMPORAIRE and instance.duree_annees:
        instance.date_fin = instance.date_debut + timedelta(days=365 * instance.duree_annees)
    elif instance.type_concession == Concession.TypeConcession.PERPETUELLE:
        instance.date_fin = None


@receiver(post_save, sender=Concession)
def synchroniser_statut_caveau(sender, instance, created, **kwargs):
    """Synchronise le statut du caveau avec le cycle de vie de la concession."""
    if created and instance.caveau.statut == Caveau.Statut.DISPONIBLE:
        instance.caveau.statut = Caveau.Statut.RESERVE
        instance.caveau.save(update_fields=['statut', 'date_modification'])
        logger.info(f"CAVEAU_AUTO_RESERVED: {instance.caveau.code} via concession {instance.numero_contrat}")
    
    if instance.statut == Concession.StatutConcession.RESILIEE:
        autres_actives = Concession.objects.filter(
            caveau=instance.caveau,
            statut=Concession.StatutConcession.ACTIVE
        ).exclude(id=instance.id).count()
        
        if autres_actives == 0:
            instance.caveau.statut = Caveau.Statut.DISPONIBLE
            instance.caveau.save(update_fields=['statut', 'date_modification'])
            logger.info(f"CAVEAU_AUTO_FREED: {instance.caveau.code} après résiliation")


@receiver(post_save, sender=Inhumation)
def valider_caveau_apres_inhumation(sender, instance, created, **kwargs):
    """Passe automatiquement le caveau en OCCUPE après enregistrement d'une inhumation."""
    if created:
        if instance.caveau.statut in [Caveau.Statut.DISPONIBLE, Caveau.Statut.RESERVE]:
            instance.caveau.statut = Caveau.Statut.OCCUPE
            instance.caveau.save(update_fields=['statut', 'date_modification'])
            logger.info(f"CAVEAU_AUTO_OCCUPIED: {instance.caveau.code} after inhumation")


@receiver(post_save, sender=DemandeExhumation)
def loger_changement_statut_exhumation(sender, instance, created, **kwargs):
    """Journalise les changements de statut des demandes d'exhumation (Audit Trail)."""
    if not created:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            if old_instance.statut != instance.statut:
                logger.info(
                    f"EXHUMATION_STATUS_CHANGED: id={instance.id}, "
                    f"old={old_instance.statut}, new={instance.statut}, "
                    f"by={instance.valide_by.email if instance.valide_by else 'system'}"
                )
        except sender.DoesNotExist:
            pass