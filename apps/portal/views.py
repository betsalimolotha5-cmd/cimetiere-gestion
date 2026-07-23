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
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache


@login_required
def dashboard_admin(request):
    """Dashboard admin optimisé - Cache de 5 minutes."""
    
    if not request.user.is_staff:
        messages.error(request, "Accès réservé aux administrateurs.")
        return redirect('carte_publique')
    
    # ⭐ CACHE : Évite de recalculer à chaque chargement
    cache_key = f'dashboard_admin_{request.user.id}'
    cached_data = cache.get(cache_key)
    
    if cached_data:
        return render(request, 'portal/dashboard_admin.html', cached_data)
    
    # ============================================
    # 1. STATISTIQUES TERRAIN (1 seule requête optimisée)
    # ============================================
    stats_caveaux = Caveau.objects.aggregate(
        total=Count('id'),
        disponibles=Count('id', filter=Q(statut='DISPONIBLE')),
        reserves=Count('id', filter=Q(statut='RESERVE')),
        occupes=Count('id', filter=Q(statut='OCCUPE')),
        non_exploitables=Count('id', filter=Q(statut='NON_EXPLOITABLE')),
    )
    
    total_caveaux = stats_caveaux['total'] or 0
    caveaux_disponibles = stats_caveaux['disponibles'] or 0
    caveaux_reserves = stats_caveaux['reserves'] or 0
    caveaux_occupes = stats_caveaux['occupes'] or 0
    caveaux_non_exploitables = stats_caveaux['non_exploitables'] or 0
    total_zones = Zone.objects.count()
    
    taux_occupation = round((caveaux_occupes / total_caveaux * 100), 1) if total_caveaux > 0 else 0
    
    # ============================================
    # 2. RÉSERVATIONS (1 seule requête)
    # ============================================
    reservations_qs = DemandeReservation.objects.filter(
        statut=DemandeReservation.Statut.EN_ATTENTE
    ).select_related('client', 'caveau', 'caveau__zone').order_by('-date_creation')
    
    total_reservations_attente = reservations_qs.count()
    reservations_en_attente = reservations_qs[:10]
    
    # ============================================
    # 3. FINANCES (requêtes groupées)
    # ============================================
    revenus_agg = Paiement.objects.filter(
        statut=Paiement.StatutPaiement.VALIDE
    ).aggregate(total=Sum('montant'))
    revenus_totaux = revenus_agg['total'] or 0
    
    revenus_par_mode = list(
        Paiement.objects.filter(statut=Paiement.StatutPaiement.VALIDE)
        .values('mode_paiement')
        .annotate(total=Sum('montant'), count=Count('id'))
        .order_by('-total')
    )
    
    paiements_recents = Paiement.objects.select_related(
        'client', 'facture'
    ).order_by('-date_paiement')[:10]
    
    # ⭐ Revenus mensuels optimisés (1 seule requête au lieu de 6)
    six_mois_avant = timezone.now() - timedelta(days=180)
    paiements_mensuels = Paiement.objects.filter(
        statut=Paiement.StatutPaiement.VALIDE,
        date_paiement__gte=six_mois_avant
    ).extra(
        select={'mois': "TO_CHAR(date_paiement, 'YYYY-MM')"}
    ).values('mois').annotate(total=Sum('montant')).order_by('mois')
    
    revenus_mensuels = [
        {'mois': p['mois'], 'total': float(p['total'])}
        for p in paiements_mensuels
    ]
    
    # ============================================
    # 4. FACTURES
    # ============================================
    factures_stats = Facture.objects.aggregate(
        total=Count('id'),
        impayees=Count('id', filter=Q(statut=Facture.StatutFacture.EN_ATTENTE)),
        payees=Count('id', filter=Q(statut=Facture.StatutFacture.PAYEE)),
    )
    
    total_factures = factures_stats['total'] or 0
    factures_impayees = factures_stats['impayees'] or 0
    factures_payees = factures_stats['payees'] or 0
    factures_recents = Facture.objects.select_related(
        'client', 'concession'
    ).order_by('-date_creation')[:10]
    
    # ============================================
    # 5. UTILISATEURS
    # ============================================
    from apps.accounts.models import User
    total_users = User.objects.filter(is_active=True).count()
    admins_count = User.objects.filter(is_staff=True).count()
    
    # ============================================
    # 6. OCCUPATION PAR ZONE (1 requête au lieu de N)
    # ============================================
    occupation_par_zone = list(
        Zone.objects.annotate(
            total_caveaux=Count('caveaux'),
            caveaux_occupes=Count('caveaux', filter=Q(caveaux__statut='OCCUPE'))
        ).values('nom', 'total_caveaux', 'caveaux_occupes')[:10]
    )
    
    # Calcul du taux
    for zone in occupation_par_zone:
        total = zone['total_caveaux'] or 0
        occupes = zone['caveaux_occupes'] or 0
        zone['taux'] = round((occupes / total * 100), 1) if total > 0 else 0
        zone['total'] = total
        zone['occupes'] = occupes
    
    # ============================================
    # 7. AUDIT
    # ============================================
    actions_recentes = DemandeReservation.objects.filter(
        statut__in=[DemandeReservation.Statut.VALIDEE, DemandeReservation.Statut.REFUSEE]
    ).select_related('client', 'caveau', 'traite_par').order_by('-date_modification')[:10]
    
    context = {
        'total_caveaux': total_caveaux,
        'caveaux_disponibles': caveaux_disponibles,
        'caveaux_reserves': caveaux_reserves,
        'caveaux_occupes': caveaux_occupes,
        'caveaux_non_exploitables': caveaux_non_exploitables,
        'total_zones': total_zones,
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
    
    # ⭐ Sauvegarde en cache pour 5 minutes
    cache.set(cache_key, context, timeout=300)
    
    return render(request, 'portal/dashboard_admin.html', context)


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
            'longitude': position['lng'] if position else None,
            'latitude': position['lat'] if position else None,
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


from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta


@login_required
def dashboard_admin(request):
    """Dashboard administrateur complet - Conforme CDC sections 2.2, 2.5, 2.6, 4, 7."""
    
    # Vérifier que l'utilisateur est admin
    if not request.user.is_staff:
        messages.error(request, "Accès réservé aux administrateurs.")
        return redirect('carte_publique')
    
    # ============================================
    # 1. STATISTIQUES GLOBALES DU TERRAIN (CDC 2.2)
    # ============================================
    try:
        total_caveaux = Caveau.objects.count()
        caveaux_disponibles = Caveau.objects.filter(statut='DISPONIBLE').count()
        caveaux_reserves = Caveau.objects.filter(statut='RESERVE').count()
        caveaux_occupes = Caveau.objects.filter(statut='OCCUPE').count()
        caveaux_non_exploitables = Caveau.objects.filter(statut='NON_EXPLOITABLE').count()
        total_zones = Zone.objects.count()
        
        # Taux d'occupation
        taux_occupation = round((caveaux_occupes / total_caveaux * 100), 1) if total_caveaux > 0 else 0
    except Exception as e:
        print(f"[DASHBOARD] Erreur stats terrain: {e}")
        total_caveaux = caveaux_disponibles = caveaux_reserves = caveaux_occupes = 0
        caveaux_non_exploitables = total_zones = taux_occupation = 0
    
    # ============================================
    # 2. RÉSERVATIONS (CDC 2.4)
    # ============================================
    try:
        reservations_en_attente = DemandeReservation.objects.filter(
            statut=DemandeReservation.Statut.EN_ATTENTE
        ).select_related('client', 'caveau', 'caveau__zone').order_by('-date_creation')[:10]
        
        total_reservations_attente = DemandeReservation.objects.filter(
            statut=DemandeReservation.Statut.EN_ATTENTE
        ).count()
    except Exception as e:
        print(f"[DASHBOARD] Erreur réservations: {e}")
        reservations_en_attente = []
        total_reservations_attente = 0
    
    # ============================================
    # 3. FINANCES (CDC 2.6)
    # ============================================
    try:
        # Revenus totaux
        revenus_totaux = Paiement.objects.filter(
            statut=Paiement.StatutPaiement.VALIDE
        ).aggregate(total=Sum('montant'))['total'] or 0
        
        # Revenus par mode de paiement
        revenus_par_mode = Paiement.objects.filter(
            statut=Paiement.StatutPaiement.VALIDE
        ).values('mode_paiement').annotate(
            total=Sum('montant'),
            count=Count('id')
        ).order_by('-total')
        
        # Paiements récents
        paiements_recents = Paiement.objects.all().select_related(
            'client', 'facture'
        ).order_by('-date_paiement')[:10]
        
        # Revenus mensuels (6 derniers mois)
        revenus_mensuels = []
        for i in range(5, -1, -1):
            date_debut = timezone.now().replace(day=1) - timedelta(days=i*30)
            date_fin = date_debut + timedelta(days=30)
            total_mois = Paiement.objects.filter(
                statut=Paiement.StatutPaiement.VALIDE,
                date_paiement__gte=date_debut,
                date_paiement__lt=date_fin
            ).aggregate(total=Sum('montant'))['total'] or 0
            revenus_mensuels.append({
                'mois': date_debut.strftime('%b %Y'),
                'total': float(total_mois)
            })
    except Exception as e:
        print(f"[DASHBOARD] Erreur finances: {e}")
        revenus_totaux = 0
        revenus_par_mode = []
        paiements_recents = []
        revenus_mensuels = []
    
    # ============================================
    # 4. FACTURES (CDC 2.6)
    # ============================================
    try:
        total_factures = Facture.objects.count()
        factures_impayees = Facture.objects.filter(statut=Facture.StatutFacture.EN_ATTENTE).count()
        factures_payees = Facture.objects.filter(statut=Facture.StatutFacture.PAYEE).count()
        factures_recents = Facture.objects.all().select_related(
            'client', 'concession'
        ).order_by('-date_creation')[:10]
    except Exception as e:
        print(f"[DASHBOARD] Erreur factures: {e}")
        total_factures = factures_impayees = factures_payees = 0
        factures_recents = []
    
    # ============================================
    # 5. UTILISATEURS
    # ============================================
    try:
        from apps.accounts.models import User
        total_users = User.objects.filter(is_active=True).count()
        admins_count = User.objects.filter(is_staff=True).count()
    except Exception as e:
        print(f"[DASHBOARD] Erreur users: {e}")
        total_users = admins_count = 0
    
    # ============================================
    # 6. TAUX D'OCCUPATION PAR ZONE (CDC 7)
    # ============================================
    try:
        occupation_par_zone = []
        for zone in Zone.objects.all()[:10]:
            total_zone = Caveau.objects.filter(zone=zone).count()
            occupes_zone = Caveau.objects.filter(zone=zone, statut='OCCUPE').count()
            taux = round((occupes_zone / total_zone * 100), 1) if total_zone > 0 else 0
            occupation_par_zone.append({
                'nom': zone.nom,
                'total': total_zone,
                'occupes': occupes_zone,
                'taux': taux
            })
    except Exception as e:
        print(f"[DASHBOARD] Erreur occupation par zone: {e}")
        occupation_par_zone = []
    
    # ============================================
    # 7. AUDIT TRAIL (CDC 4) - Dernières actions
    # ============================================
    try:
        # Récupérer les dernières réservations validées comme "audit"
        actions_recentes = DemandeReservation.objects.filter(
            statut__in=[DemandeReservation.Statut.VALIDEE, DemandeReservation.Statut.REFUSEE]
        ).select_related('client', 'caveau', 'traite_par').order_by('-date_modification')[:10]
    except Exception as e:
        print(f"[DASHBOARD] Erreur audit: {e}")
        actions_recentes = []
    
    context = {
        # Terrain
        'total_caveaux': total_caveaux,
        'caveaux_disponibles': caveaux_disponibles,
        'caveaux_reserves': caveaux_reserves,
        'caveaux_occupes': caveaux_occupes,
        'caveaux_non_exploitables': caveaux_non_exploitables,
        'total_zones': total_zones,
        'taux_occupation': taux_occupation,
        
        # Réservations
        'reservations_en_attente': reservations_en_attente,
        'total_reservations_attente': total_reservations_attente,
        
        # Finances
        'revenus_totaux': revenus_totaux,
        'revenus_par_mode': list(revenus_par_mode),
        'paiements_recents': paiements_recents,
        'revenus_mensuels': revenus_mensuels,
        
        # Factures
        'total_factures': total_factures,
        'factures_impayees': factures_impayees,
        'factures_payees': factures_payees,
        'factures_recents': factures_recents,
        
        # Users
        'total_users': total_users,
        'admins_count': admins_count,
        
        # Occupation par zone
        'occupation_par_zone': occupation_par_zone,
        
        # Audit
        'actions_recentes': actions_recentes,
    }
    
    return render(request, 'portal/dashboard_admin.html', context)