"""
Vues du portail client (Carte publique + Réservations + Factures + Paiements + Dashboards).
Conforme au CDC : workflow complet de réservation → facturation → paiement + carte dynamique + RBAC.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from django.db.models import Sum, Count, Q, F
from django.core.cache import cache

from .models import DemandeReservation
from apps.core.models import Caveau, Zone, ParametreCimetiere
from apps.billing.models import Facture, Paiement
from apps.accounts.models import User


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
    """
    context = {
        'nombre_zones': Zone.objects.count(),
        'nombre_caveaux': Caveau.objects.count(),
        'nombre_disponibles': Caveau.objects.filter(statut='DISPONIBLE').count(),
    }
    return render(request, 'portal/carte_publique.html', context)


def api_carte_publique(request):
    """
    API JSON qui renvoie les données de la carte + le périmètre dynamique du cimetière.
    Gère le code couleur dynamique selon le CDC.
    """
    # Récupérer les IDs des caveaux avec demande EN_ATTENTE → ORANGE
    caveaux_en_attente_ids = set(
        DemandeReservation.objects.filter(
            statut='EN_ATTENTE'
        ).values_list('caveau_id', flat=True)
    )
    
    # Récupérer les IDs des caveaux avec demande VALIDEE → ROUGE
    caveaux_valides_ids = set(
        DemandeReservation.objects.filter(
            statut='VALIDEE'
        ).values_list('caveau_id', flat=True)
    )

    caveaux_data = []
    for caveau in Caveau.objects.select_related('zone').all():
        # PRIORITÉ 1 : Statut réel du caveau
        if caveau.statut == 'NON_EXPLOITABLE':
            couleur, statut_affiche, reservable = '#95a5a6', 'Non exploitable', False
        elif caveau.statut == 'OCCUPE':
            couleur, statut_affiche, reservable = '#e74c3c', 'Occupé', False
        elif caveau.statut == 'RESERVE':
            couleur, statut_affiche, reservable = '#f39c12', 'Réservé', False
        # PRIORITÉ 2 : Statut de la demande (si caveau DISPONIBLE)
        elif caveau.statut == 'DISPONIBLE':
            if caveau.id in caveaux_valides_ids:
                couleur, statut_affiche, reservable = '#f39c12', 'Réservé (validation en cours)', False
            elif caveau.id in caveaux_en_attente_ids:
                couleur, statut_affiche, reservable = '#f39c12', 'En attente de validation', False
            else:
                couleur, statut_affiche, reservable = '#27ae60', 'Disponible', True
        else:
            couleur, statut_affiche, reservable = '#27ae60', 'Disponible', True

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
            'longitude': position['lng'] if position else None,
            'latitude': position['lat'] if position else None,
        })

    # ============================================
    # ⭐ Récupération dynamique du périmètre et du centre
    # ============================================
    # MODIFICATION : Coordonnées par défaut centrées sur Pointe-Noire [Lat, Lng]
    centre_data = [-4.7692, 11.8644] 
    perimetre_data = []
    
    try:
        parametres = ParametreCimetiere.objects.first()
        if parametres:
            # 1. Centre (Format Leaflet: [Latitude, Longitude])
            if hasattr(parametres, 'coordonnees_centre') and parametres.coordonnees_centre:
                centre_data = [parametres.coordonnees_centre.y, parametres.coordonnees_centre.x]
            
            # 2. Périmètre (Format Leaflet: [[Lat, Lng], [Lat, Lng], ...])
            if hasattr(parametres, 'perimetre') and parametres.perimetre:
                # GeoDjango renvoie (Lng, Lat), on inverse pour Leaflet (Lat, Lng)
                perimetre_data = [[coord[1], coord[0]] for coord in parametres.perimetre.coords[0]]
    except Exception as e:
        print(f"⚠️ Impossible de charger le périmètre dynamique depuis la BDD: {e}")

    return JsonResponse({
        'caveaux': caveaux_data,
        'centre': centre_data,
        'perimetre': perimetre_data
    }, safe=False)


@login_required
def reservation_form(request, caveau_id):
    """Formulaire de réservation pour un caveau donné."""
    caveau = get_object_or_404(Caveau, id=caveau_id)

    if caveau.statut != 'DISPONIBLE':
        messages.error(request, 'Ce caveau n\'est plus disponible.')
        return redirect('carte_publique')

    if DemandeReservation.objects.filter(
        caveau=caveau,
        statut='EN_ATTENTE'
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
        if not defunt_nom: erreurs.append('Le nom du défunt est obligatoire.')
        if not defunt_prenom: erreurs.append('Le prénom du défunt est obligatoire.')
        if not date_deces: erreurs.append('La date de décès est obligatoire.')
        if not lien_parente: erreurs.append('Le lien de parenté est obligatoire.')
        if not telephone: erreurs.append('Le téléphone de contact est obligatoire.')

        if erreurs:
            for e in erreurs:
                messages.error(request, e)
        else:
            reservation = DemandeReservation.objects.create(
                client=request.user,
                caveau=caveau,
                defunt_nom=defunt_nom,
                defunt_prenom=defunt_prenom,
                date_deces=date_deces,
                lien_parente=lien_parente,
                telephone_contact=telephone,
                statut='EN_ATTENTE',
            )
            
            try:
                from apps.notifications.services import NotificationService
                admins = User.objects.filter(is_staff=True, is_active=True)
                for admin_user in admins:
                    NotificationService.creer_notification(
                        utilisateur=admin_user,
                        titre='📋 Nouvelle demande de réservation',
                        message=f'Nouvelle demande pour le caveau {caveau.code} par {request.user.get_full_name() or request.user.email}.',
                        url_lien=f'/admin/portal/demandereservation/{reservation.id}/change/'
                    )
            except Exception:
                pass
            
            messages.success(request, f'Votre demande de réservation pour le caveau {caveau.code} a été soumise avec succès.')
            return redirect('mes_reservations')

    return render(request, 'portal/reservation_form.html', {'caveau': caveau})


@login_required
def mes_reservations(request):
    """Liste des réservations du client connecté."""
    reservations = DemandeReservation.objects.filter(
        client=request.user
    ).select_related('caveau', 'caveau__zone', 'traite_par')
    return render(request, 'portal/mes_reservations.html', {'reservations': reservations})


@login_required
def mes_factures(request):
    """Liste des factures du client connecté."""
    factures = Facture.objects.filter(
        client=request.user
    ).select_related('concession', 'concession__caveau', 'concession__caveau__zone')
    return render(request, 'portal/mes_factures.html', {'factures': factures})


@login_required
def facture_detail(request, facture_id):
    """Détail d'une facture avec option de paiement."""
    facture = get_object_or_404(Facture, id=facture_id, client=request.user)
    paiements = Paiement.objects.filter(facture=facture).order_by('-date_paiement')
    return render(request, 'portal/facture_detail.html', {'facture': facture, 'paiements': paiements})


@login_required
def payer_facture(request, facture_id):
    """Formulaire de paiement pour une facture."""
    facture = get_object_or_404(Facture, id=facture_id, client=request.user)
    
    if facture.est_payee():
        messages.info(request, 'Cette facture est déjà entièrement payée.')
        return redirect('facture_detail', facture_id=facture.id)
    
    if facture.statut == 'ANNULEE':
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
            if montant <= 0: erreurs.append('Le montant doit être supérieur à 0.')
            if montant > facture.montant_restant: erreurs.append(f'Le montant ne peut pas dépasser {facture.montant_restant} FCFA.')
        except:
            erreurs.append('Montant invalide.')
        
        if not mode_paiement: erreurs.append('Le mode de paiement est obligatoire.')
        if mode_paiement in ['MOBILE_MONEY', 'AIRTEL_MONEY'] and not telephone:
            erreurs.append('Le numéro de téléphone est obligatoire pour Mobile Money.')

        if erreurs:
            for e in erreurs:
                messages.error(request, e)
        else:
            paiement = Paiement.objects.create(
                facture=facture,
                client=request.user,
                montant=montant,
                mode_paiement=mode_paiement,
                reference_transaction=reference,
                numero_telephone=telephone,
                statut='EN_ATTENTE',
            )
            
            try:
                from apps.notifications.services import NotificationService
                NotificationService.creer_notification(
                    utilisateur=request.user,
                    titre='💳 Paiement enregistré',
                    message=f'Votre paiement de {montant:,.0f} FCFA pour la facture {facture.numero_facture} est en attente de validation.',
                    url_lien=f'/portal/facture/{facture.id}/'
                )
            except Exception:
                pass
            
            messages.success(request, f'Votre paiement de {montant:,.0f} FCFA a été enregistré avec succès.')
            return redirect('facture_detail', facture_id=facture.id)

    return render(request, 'portal/payer_facture.html', {'facture': facture})


# ==============================================================================
# ⭐ NOUVEAU : DASHBOARD AGENT DE TERRAIN (RBAC)
# ==============================================================================
@login_required
def dashboard_agent(request):
    """Tableau de bord simplifié et opérationnel pour les agents de terrain."""
    
    # Vérifier que l'utilisateur est dans le groupe "Agents"/"Agent" ou est staff
    user_groups = request.user.groups.values_list('name', flat=True)
    is_agent = 'Agents' in user_groups or 'Agent' in user_groups
    
    if not request.user.is_staff and not is_agent:
        messages.error(request, "Accès réservé aux agents de terrain et administrateurs.")
        return redirect('carte_publique')
    
    try:
        caveaux_disponibles = Caveau.objects.filter(statut='DISPONIBLE').count()
        total_zones = Zone.objects.filter(est_exploitable=True).count()
        
        reservations_en_attente = DemandeReservation.objects.filter(
            statut='EN_ATTENTE'
        ).select_related('client', 'caveau', 'caveau__zone').order_by('-date_creation')[:10]
        
        total_reservations_attente = DemandeReservation.objects.filter(
            statut='EN_ATTENTE'
        ).count()
    except Exception as e:
        print(f"[DASHBOARD AGENT] Erreur: {e}")
        caveaux_disponibles = 0
        total_zones = 0
        total_reservations_attente = 0
        reservations_en_attente = []

    context = {
        'caveaux_disponibles': caveaux_disponibles,
        'total_zones': total_zones,
        'reservations_en_attente': reservations_en_attente,
        'total_reservations_attente': total_reservations_attente,
    }
    
    return render(request, 'portal/dashboard_agent.html', context)


# ==============================================================================
# DASHBOARD ADMINISTRATEUR
# ==============================================================================
@login_required
def dashboard_admin(request):
    """Dashboard admin optimisé - Cache de 5 minutes. Conforme CDC."""
    if not request.user.is_staff:
        messages.error(request, "Accès réservé aux administrateurs.")
        return redirect('carte_publique')
    
    cache_key = f'dashboard_admin_{request.user.id}'
    cached_data = cache.get(cache_key)
    if cached_data:
        return render(request, 'portal/dashboard_admin.html', cached_data)
    
    # Valeurs par défaut (fallback sécurisé)
    total_caveaux = caveaux_disponibles = caveaux_reserves = caveaux_occupes = caveaux_non_exploitables = 0
    taux_occupation = 0
    total_reservations_attente = 0
    reservations_en_attente = []
    revenus_totaux = 0
    revenus_par_mode = []
    paiements_recents = []
    revenus_mensuels = []
    total_factures = factures_impayees = factures_payees = 0
    factures_recents = []
    total_users = admins_count = 0
    occupation_par_zone = []
    actions_recentes = []

    try:
        # 1. STATISTIQUES TERRAIN
        stats_caveaux = Caveau.objects.aggregate(
            total=Count('id'),
            disponibles=Count('id', filter=Q(statut='DISPONIBLE')),
            reserves=Count('id', filter=Q(statut='RESERVE')),
            occupes=Count('id', filter=Q(statut='OCCUPE')),
            non_exploitables=Count('id', filter=Q(statut='NON_EXPLOITABLE')),
        )
        total_caveaux = stats_caveaux['total'] or 0
        taux_occupation = round((stats_caveaux['occupes'] / total_caveaux * 100), 1) if total_caveaux > 0 else 0
        
        # 2. RÉSERVATIONS (Utilisation de chaînes de caractères)
        reservations_qs = DemandeReservation.objects.filter(statut='EN_ATTENTE').select_related('client', 'caveau', 'caveau__zone').order_by('-date_creation')
        total_reservations_attente = reservations_qs.count()
        reservations_en_attente = list(reservations_qs[:10])
        
        # 3. FINANCES
        revenus_agg = Paiement.objects.filter(statut='VALIDE').aggregate(total=Sum('montant'))
        revenus_totaux = revenus_agg['total'] or 0
        
        revenus_par_mode = list(Paiement.objects.filter(statut='VALIDE')
            .values('mode_paiement')
            .annotate(total=Sum('montant'), count=Count('id'))
            .order_by('-total'))
            
        paiements_recents = list(Paiement.objects.select_related('client', 'facture').order_by('-date_paiement')[:10])
        
        six_mois_avant = timezone.now() - timedelta(days=180)
        paiements_mensuels = Paiement.objects.filter(statut='VALIDE', date_paiement__gte=six_mois_avant).extra(
            select={'mois': "TO_CHAR(date_paiement, 'YYYY-MM')"}
        ).values('mois').annotate(total=Sum('montant')).order_by('mois')
        revenus_mensuels = [{'mois': p['mois'], 'total': float(p['total'])} for p in paiements_mensuels]
        
        # 4. FACTURES (Chaînes de caractères)
        factures_stats = Facture.objects.aggregate(
            total=Count('id'), 
            impayees=Count('id', filter=Q(statut='EN_ATTENTE')), 
            payees=Count('id', filter=Q(statut='PAYEE'))
        )
        total_factures = factures_stats['total'] or 0
        factures_impayees = factures_stats['impayees'] or 0
        factures_payees = factures_stats['payees'] or 0
        factures_recents = list(Facture.objects.select_related('client', 'concession').order_by('-date_creation')[:10])
        
        # 5. UTILISATEURS
        total_users = User.objects.filter(is_active=True).count()
        admins_count = User.objects.filter(is_staff=True).count()
        
        # 6. OCCUPATION PAR ZONE
        occupation_par_zone = list(Zone.objects.annotate(
            total_caveaux=Count('caveaux'), 
            caveaux_occupes=Count('caveaux', filter=Q(caveaux__statut='OCCUPE'))
        ).values('nom', 'total_caveaux', 'caveaux_occupes')[:10])
        
        for zone in occupation_par_zone:
            total = zone['total_caveaux'] or 0
            zone['taux'] = round((zone['caveaux_occupes'] / total * 100), 1) if total > 0 else 0
            zone['total'] = total
            zone['occupes'] = zone['caveaux_occupes'] or 0
            
        # 7. AUDIT
        actions_recentes = list(DemandeReservation.objects.filter(
            statut__in=['VALIDEE', 'REFUSEE']
        ).select_related('client', 'caveau', 'traite_par').order_by('-date_modification')[:10])
        
    except Exception as e:
        print(f"[DASHBOARD] Erreur générale (ignorée pour fallback sécurisé) : {e}")

    context = {
        'total_caveaux': total_caveaux,
        'caveaux_disponibles': stats_caveaux['disponibles'] if 'disponibles' in stats_caveaux else 0,
        'caveaux_reserves': stats_caveaux['reserves'] if 'reserves' in stats_caveaux else 0,
        'caveaux_occupes': stats_caveaux['occupes'] if 'occupes' in stats_caveaux else 0,
        'caveaux_non_exploitables': stats_caveaux['non_exploitables'] if 'non_exploitables' in stats_caveaux else 0,
        'total_zones': Zone.objects.count(),
        'taux_occupation': taux_occupation,
        'reservations_en_attente': reservations_en_attente,
        'total_reservations_attente': total_reservations_attente,
        'revenus_totaux': revenus_totaux,
        'revenus_par_mode': revenus_par_mode,
        'paiements_recents': paiements_recents,
        'revenus_mensuels': revenus_mensuels,
        'total_factures': total_factures,
        'factures_impayees': factures_impayees,
        'factures_payees': factures_payees,
        'factures_recents': factures_recents,
        'total_users': total_users,
        'admins_count': admins_count,
        'occupation_par_zone': occupation_par_zone,
        'actions_recentes': actions_recentes,
    }
    
    cache.set(cache_key, context, timeout=300)
    return render(request, 'portal/dashboard_admin.html', context)