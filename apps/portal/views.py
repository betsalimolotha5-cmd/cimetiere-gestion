"""
Vues du portail client (Carte publique + Réservations + Factures + Paiements).
Conforme au CDC : workflow complet de réservation → facturation → paiement.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from .models import DemandeReservation
from apps.core.models import Caveau, Zone
from apps.billing.models import Facture, Paiement
from decimal import Decimal


def extraire_coordonnees(point_gps):
    """
    Extrait les coordonnées d'un objet Point (PostGIS) en tuple (lng, lat).
    Retourne None si le point est vide.
    """
    if not point_gps:
        return None
    try:
        return {'lng': point_gps.x, 'lat': point_gps.y}
    except (AttributeError, TypeError):
        return None


def carte_publique(request):
    """
    Page publique avec la carte interactive du cimetière.
    Accessible sans authentification.
    Code couleur :
      - Vert   : Disponible
      - Orange : Réservé / En attente de validation
      - Rouge  : Occupé / Validé
      - Gris   : Non exploitable
    """
    context = {
        'nombre_zones': Zone.objects.count(),
        'nombre_caveaux': Caveau.objects.count(),
        'nombre_disponibles': Caveau.objects.filter(statut='DISPONIBLE').count(),
    }
    return render(request, 'portal/carte_publique.html', context)


def api_carte_publique(request):
    """
    API JSON qui renvoie les données de la carte.
    Gère le code couleur dynamique selon le CDC.
    PRIORITÉ : Statut réel du caveau > Statut de la demande
    """
    # Récupérer les IDs des caveaux avec demande EN_ATTENTE → ORANGE
    caveaux_en_attente_ids = set(
        DemandeReservation.objects.filter(
            statut=DemandeReservation.Statut.EN_ATTENTE
        ).values_list('caveau_id', flat=True)
    )
    
    # Récupérer les IDs des caveaux avec demande VALIDEE → ROUGE
    caveaux_valides_ids = set(
        DemandeReservation.objects.filter(
            statut=DemandeReservation.Statut.VALIDEE
        ).values_list('caveau_id', flat=True)
    )

    caveaux_data = []
    for caveau in Caveau.objects.select_related('zone').all():
        # PRIORITÉ 1 : Statut réel du caveau (le plus important)
        if caveau.statut == 'NON_EXPLOITABLE':
            couleur = '#95a5a6'  # Gris
            statut_affiche = 'Non exploitable'
            reservable = False
        elif caveau.statut == 'OCCUPE':
            couleur = '#e74c3c'  # Rouge
            statut_affiche = 'Occupé'
            reservable = False
        elif caveau.statut == 'RESERVE':
            couleur = '#f39c12'  # Orange
            statut_affiche = 'Réservé'
            reservable = False
        # PRIORITÉ 2 : Statut de la demande (si caveau DISPONIBLE)
        elif caveau.statut == 'DISPONIBLE':
            if caveau.id in caveaux_valides_ids:
                # Il y a une demande validée mais le caveau n'a pas été mis à jour
                # On le montre quand même comme réservé (orange) pour éviter la confusion
                couleur = '#f39c12'  # Orange
                statut_affiche = 'Réservé (validation en cours)'
                reservable = False
            elif caveau.id in caveaux_en_attente_ids:
                couleur = '#f39c12'  # Orange
                statut_affiche = 'En attente de validation'
                reservable = False
            else:
                # Vraiment disponible
                couleur = '#27ae60'  # Vert
                statut_affiche = 'Disponible'
                reservable = True
        else:
            # Par défaut, considérer comme disponible
            couleur = '#27ae60'
            statut_affiche = 'Disponible'
            reservable = True

        # Coordonnées GPS
        position = None
        if hasattr(caveau, 'position_gps') and caveau.position_gps:
            position = extraire_coordonnees(caveau.position_gps)
        elif hasattr(caveau, 'coordonnees_gps') and caveau.coordonnees_gps:
            position = extraire_coordonnees(caveau.coordonnees_gps)

        caveaux_data.append({
            'id': caveau.id,
            'code': caveau.code,
            'zone': caveau.zone.nom if caveau.zone else '',
            'type_caveau': caveau.get_type_caveau_display(),
            'statut': caveau.statut,
            'statut_affiche': statut_affiche,
            'couleur': couleur,
            'reservable': reservable,
            'position': position,
            'prix': float(caveau.prix_concession) if caveau.prix_concession else 0,
        })

    return JsonResponse({'caveaux': caveaux_data}, safe=False)


@login_required
def reservation_form(request, caveau_id):
    """Formulaire de réservation pour un caveau donné."""
    caveau = get_object_or_404(Caveau, id=caveau_id)

    if caveau.statut != 'DISPONIBLE':
        messages.error(request, 'Ce caveau n\'est plus disponible.')
        return redirect('carte_publique')

    if DemandeReservation.objects.filter(
        caveau=caveau,
        statut=DemandeReservation.Statut.EN_ATTENTE
    ).exists():
        messages.warning(request, 'Ce caveau est déjà en cours de réservation.')
        return redirect('carte_publique')

    if request.method == 'POST':
        defunt_nom = request.POST.get('defunt_nom', '').strip()
        defunt_prenom = request.POST.get('defunt_prenom', '').strip()
        date_deces = request.POST.get('date_deces', '').strip()
        lien_parente = request.POST.get('lien_parente', '').strip()
        telephone = request.POST.get('telephone_contact', '').strip()

        erreurs = []
        if not defunt_nom:
            erreurs.append('Le nom du défunt est obligatoire.')
        if not defunt_prenom:
            erreurs.append('Le prénom du défunt est obligatoire.')
        if not date_deces:
            erreurs.append('La date de décès est obligatoire.')
        if not lien_parente:
            erreurs.append('Le lien de parenté est obligatoire.')
        if not telephone:
            erreurs.append('Le téléphone de contact est obligatoire.')

        if erreurs:
            for e in erreurs:
                messages.error(request, e)
        else:
            # Créer la demande de réservation
            reservation = DemandeReservation.objects.create(
                client=request.user,
                caveau=caveau,
                defunt_nom=defunt_nom,
                defunt_prenom=defunt_prenom,
                date_deces=date_deces,
                lien_parente=lien_parente,
                telephone_contact=telephone,
                statut=DemandeReservation.Statut.EN_ATTENTE,
            )
            
            # Notifier les administrateurs
            try:
                from apps.notifications.services import NotificationService
                from apps.accounts.models import User
                
                admins = User.objects.filter(is_staff=True, is_active=True)
                for admin_user in admins:
                    NotificationService.creer_notification(
                        utilisateur=admin_user,
                        titre=f'📋 Nouvelle demande de réservation',
                        message=f'Nouvelle demande pour le caveau {caveau.code} par {request.user.get_full_name() or request.user.email}.',
                        url_lien=f'/admin/portal/demandereservation/{reservation.id}/change/'
                    )
            except Exception as e:
                pass  # Ne pas bloquer si la notification échoue
            
            messages.success(
                request,
                f'Votre demande de réservation pour le caveau {caveau.code} '
                f'a été soumise avec succès. Elle est en attente de validation.'
            )
            return redirect('mes_reservations')

    context = {
        'caveau': caveau,
    }
    return render(request, 'portal/reservation_form.html', context)


@login_required
def mes_reservations(request):
    """Liste des réservations du client connecté."""
    reservations = DemandeReservation.objects.filter(
        client=request.user
    ).select_related('caveau', 'caveau__zone', 'traite_par')

    context = {
        'reservations': reservations,
    }
    return render(request, 'portal/mes_reservations.html', context)


@login_required
def mes_factures(request):
    """Liste des factures du client connecté."""
    factures = Facture.objects.filter(
        client=request.user
    ).select_related('concession', 'concession__caveau', 'concession__caveau__zone')

    context = {
        'factures': factures,
    }
    return render(request, 'portal/mes_factures.html', context)


@login_required
def facture_detail(request, facture_id):
    """Détail d'une facture avec option de paiement."""
    facture = get_object_or_404(Facture, id=facture_id, client=request.user)
    
    # Récupérer les paiements associés
    paiements = Paiement.objects.filter(
        facture=facture
    ).order_by('-date_paiement')

    context = {
        'facture': facture,
        'paiements': paiements,
    }
    return render(request, 'portal/facture_detail.html', context)


@login_required
def payer_facture(request, facture_id):
    """Formulaire de paiement pour une facture."""
    facture = get_object_or_404(Facture, id=facture_id, client=request.user)
    
    if facture.est_payee():
        messages.info(request, 'Cette facture est déjà entièrement payée.')
        return redirect('facture_detail', facture_id=facture.id)
    
    if facture.statut == Facture.StatutFacture.ANNULEE:
        messages.error(request, 'Cette facture a été annulée.')
        return redirect('facture_detail', facture_id=facture.id)

    if request.method == 'POST':
        montant_str = request.POST.get('montant', '').strip()
        mode_paiement = request.POST.get('mode_paiement', '').strip()
        reference = request.POST.get('reference_transaction', '').strip()
        telephone = request.POST.get('numero_telephone', '').strip()

        erreurs = []
        try:
            montant = Decimal(montant_str)
            if montant <= 0:
                erreurs.append('Le montant doit être supérieur à 0.')
            if montant > facture.montant_restant:
                erreurs.append(f'Le montant ne peut pas dépasser {facture.montant_restant} FCFA.')
        except:
            erreurs.append('Montant invalide.')
        
        if not mode_paiement:
            erreurs.append('Le mode de paiement est obligatoire.')
        
        if mode_paiement in ['MOBILE_MONEY', 'AIRTEL_MONEY'] and not telephone:
            erreurs.append('Le numéro de téléphone est obligatoire pour Mobile Money.')

        if erreurs:
            for e in erreurs:
                messages.error(request, e)
        else:
            # Créer le paiement
            paiement = Paiement.objects.create(
                facture=facture,
                client=request.user,
                montant=montant,
                mode_paiement=mode_paiement,
                reference_transaction=reference,
                numero_telephone=telephone,
                statut=Paiement.StatutPaiement.EN_ATTENTE,
            )
            
            # Notifier le client
            try:
                from apps.notifications.services import NotificationService
                NotificationService.creer_notification(
                    utilisateur=request.user,
                    titre='💳 Paiement enregistré',
                    message=f'Votre paiement de {montant:,.0f} FCFA pour la facture {facture.numero_facture} '
                            f'a été enregistré et est en attente de validation.',
                    url_lien=f'/portal/facture/{facture.id}/'
                )
            except Exception as e:
                pass  # Ne pas bloquer si la notification échoue
            
            messages.success(
                request,
                f'Votre paiement de {montant:,.0f} FCFA a été enregistré avec succès. '
                f'Il est en attente de validation par l\'administration.'
            )
            return redirect('facture_detail', facture_id=facture.id)

    context = {
        'facture': facture,
    }
    return render(request, 'portal/payer_facture.html', context)