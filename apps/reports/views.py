"""
Vues pour les rapports et statistiques.
"""
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Count, Q
from .services import RapportService
from apps.core.models import Caveau, Zone, Concession
from apps.billing.models import Facture, Paiement
from apps.accounts.models import User


@staff_member_required
def dashboard(request):
    """Tableau de bord admin avec statistiques globales et graphiques."""
    aujourd = timezone.now().date()
    
    # Statistiques globales
    total_caveaux = Caveau.objects.count()
    caveaux_disponibles = Caveau.objects.filter(statut='DISPONIBLE').count()
    caveaux_reserves = Caveau.objects.filter(statut='RESERVE').count()
    caveaux_occupes = Caveau.objects.filter(statut='OCCUPE').count()
    caveaux_non_exploitables = Caveau.objects.filter(statut='NON_EXPLOITABLE').count()
    
    taux_occupation = 0
    if total_caveaux > 0:
        taux_occupation = round((caveaux_occupes / total_caveaux) * 100, 1)
    
    # Concessions
    concessions_actives = Concession.objects.filter(statut='ACTIVE').count()
    concessions_expirent_bientot = Concession.objects.filter(
        statut='ACTIVE',
        date_fin__gte=aujourd,
        date_fin__lte=aujourd + timedelta(days=30)
    ).count()
    
    # Factures et paiements
    factures_emises = Facture.objects.count()
    factures_payees = Facture.objects.filter(statut='PAYEE').count()
    factures_en_retard = Facture.objects.filter(
        statut__in=['EMISE', 'PARTIELLEMENT_PAYEE'],
        date_echeance__lt=aujourd
    ).count()
    
    total_facture = Facture.objects.aggregate(total=Sum('montant_total'))['total'] or 0
    total_paye = Paiement.objects.filter(statut='VALIDE').aggregate(total=Sum('montant'))['total'] or 0
    total_restant = total_facture - total_paye
    
    # Paiements du mois
    debut_mois = aujourd.replace(day=1)
    paiements_mois = Paiement.objects.filter(
        date_paiement__gte=debut_mois,
        statut='VALIDE'
    ).aggregate(total=Sum('montant'))['total'] or 0
    
    # Occupation par zone
    zones_data = []
    for zone in Zone.objects.all():
        total_zone = zone.caveaux.count()
        disponibles_zone = zone.caveaux.filter(statut='DISPONIBLE').count()
        occupes_zone = zone.caveaux.filter(statut='OCCUPE').count()
        
        taux_zone = 0
        if total_zone > 0:
            taux_zone = round((occupes_zone / total_zone) * 100, 1)
        
        zones_data.append({
            'nom': zone.nom,
            'code': zone.code,
            'total': total_zone,
            'disponibles': disponibles_zone,
            'occupes': occupes_zone,
            'taux_occupation': taux_zone,
        })
    
    # Évolution mensuelle (6 derniers mois)
    evolution_mensuelle = []
    for i in range(5, -1, -1):
        date_debut = (aujourd.replace(day=1) - timedelta(days=i*30)).replace(day=1)
        date_fin = (date_debut + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        factures_mois = Facture.objects.filter(
            date_emission__gte=date_debut,
            date_emission__lte=date_fin
        ).count()
        
        total_mois = Facture.objects.filter(
            date_emission__gte=date_debut,
            date_emission__lte=date_fin
        ).aggregate(total=Sum('montant_total'))['total'] or 0
        
        evolution_mensuelle.append({
            'mois': date_debut.strftime('%b %Y'),
            'count': factures_mois,
            'total': float(total_mois),
        })
    
    # Alertes
    alertes = []
    if factures_en_retard > 0:
        alertes.append({
            'type': 'danger',
            'icon': '⚠️',
            'message': f'{factures_en_retard} facture(s) en retard de paiement',
            'url': '/admin/billing/facture/?statut__in=EMISE,PARTIELLEMENT_PAYEE'
        })
    
    if concessions_expirent_bientot > 0:
        alertes.append({
            'type': 'warning',
            'icon': '🔔',
            'message': f'{concessions_expirent_bientot} concession(s) expirent dans les 30 jours',
            'url': '/admin/core/concession/'
        })
    
    if taux_occupation > 80:
        alertes.append({
            'type': 'warning',
            'icon': '📊',
            'message': f'Taux d\'occupation élevé : {taux_occupation}%',
            'url': '/rapports/occupation/'
        })
    
    context = {
        'title': '📊 Tableau de bord',
        'stats': {
            'total_caveaux': total_caveaux,
            'caveaux_disponibles': caveaux_disponibles,
            'caveaux_reserves': caveaux_reserves,
            'caveaux_occupes': caveaux_occupes,
            'taux_occupation': taux_occupation,
            'concessions_actives': concessions_actives,
            'concessions_expirent_bientot': concessions_expirent_bientot,
            'factures_emises': factures_emises,
            'factures_payees': factures_payees,
            'factures_en_retard': factures_en_retard,
            'total_facture': float(total_facture),
            'total_paye': float(total_paye),
            'total_restant': float(total_restant),
            'paiements_mois': float(paiements_mois),
        },
        'zones_data': zones_data,
        'evolution_mensuelle': evolution_mensuelle,
        'alertes': alertes,
    }
    
    return render(request, 'reports/dashboard.html', context)


@staff_member_required
def rapport_financier(request):
    """Vue du rapport financier."""
    date_fin_str = request.GET.get('date_fin')
    date_debut_str = request.GET.get('date_debut')
    
    if date_fin_str:
        date_fin = timezone.datetime.strptime(date_fin_str, '%Y-%m-%d').date()
    else:
        date_fin = timezone.now().date()
    
    if date_debut_str:
        date_debut = timezone.datetime.strptime(date_debut_str, '%Y-%m-%d').date()
    else:
        date_debut = date_fin - timedelta(days=30)
    
    rapport = RapportService.rapport_financier(date_debut, date_fin)
    
    context = {
        'title': '📊 Rapport Financier',
        'rapport': rapport,
        'date_debut': date_debut,
        'date_fin': date_fin,
    }
    return render(request, 'reports/rapport_financier.html', context)


@staff_member_required
def rapport_occupation(request):
    """Vue du rapport d'occupation."""
    rapport = RapportService.rapport_occupation()
    
    context = {
        'title': '🗺️ Rapport d\'Occupation',
        'rapport': rapport,
    }
    return render(request, 'reports/rapport_occupation.html', context)


@staff_member_required
def rapport_concessions(request):
    """Vue du rapport des concessions."""
    rapport = RapportService.rapport_concessions()
    
    context = {
        'title': '📋 Rapport des Concessions',
        'rapport': rapport,
    }
    return render(request, 'reports/rapport_concessions.html', context)


@staff_member_required
def rapport_notifications(request):
    """Vue du rapport des notifications."""
    rapport = RapportService.rapport_notifications()
    
    context = {
        'title': '🔔 Rapport des Notifications',
        'rapport': rapport,
    }
    return render(request, 'reports/rapport_notifications.html', context)

@staff_member_required
def export_rapport_excel(request):
    """Exporte le rapport financier en Excel."""
    from openpyxl import Workbook
    from django.http import HttpResponse
    from datetime import timedelta
    
    date_fin_str = request.GET.get('date_fin')
    date_debut_str = request.GET.get('date_debut')
    
    if date_fin_str:
        date_fin = timezone.datetime.strptime(date_fin_str, '%Y-%m-%d').date()
    else:
        date_fin = timezone.now().date()
    
    if date_debut_str:
        date_debut = timezone.datetime.strptime(date_debut_str, '%Y-%m-%d').date()
    else:
        date_debut = date_fin - timedelta(days=30)
    
    rapport = RapportService.rapport_financier(date_debut, date_fin)
    
    # Créer le workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Rapport Financier"
    
    # En-tête
    ws.append(['Rapport Financier'])
    ws.append([f'Du {date_debut.strftime("%d/%m/%Y")} au {date_fin.strftime("%d/%m/%Y")}'])
    ws.append([])
    
    # Statistiques
    ws.append(['Statistiques'])
    ws.append(['Factures émises', rapport['total_factures']])
    ws.append(['Total facturé (TTC)', float(rapport['total_ttc'])])
    ws.append(['Total encaissé', float(rapport['total_paye'])])
    ws.append(['Total restant dû', float(rapport['total_restant'])])
    ws.append(['Nombre de paiements', rapport['nb_paiements']])
    ws.append(['Factures en retard', rapport['factures_en_retard']])
    ws.append([])
    
    # Paiements par mode
    if rapport['paiements_par_mode']:
        ws.append(['Paiements par mode'])
        ws.append(['Mode', 'Nombre', 'Montant total'])
        for mode in rapport['paiements_par_mode']:
            ws.append([mode['mode_paiement'], mode['count'], float(mode['total'])])
        ws.append([])
    
    # Évolution mensuelle
    if rapport['evolution_mensuelle']:
        ws.append(['Évolution mensuelle'])
        ws.append(['Mois', 'Nombre de factures', 'Montant total'])
        for mois in rapport['evolution_mensuelle']:
            ws.append([mois['mois'].strftime('%B %Y'), mois['count'], float(mois['total'])])
    
    # Créer la réponse HTTP
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="rapport_financier_{date_debut}_{date_fin}.xlsx"'
    
    wb.save(response)
    return response


@staff_member_required
def export_rapport_pdf(request):
    """Exporte le rapport financier en PDF."""
    from django.http import HttpResponse
    from django.template.loader import render_to_string
    from xhtml2pdf import pisa
    from datetime import timedelta
    
    date_fin_str = request.GET.get('date_fin')
    date_debut_str = request.GET.get('date_debut')
    
    if date_fin_str:
        date_fin = timezone.datetime.strptime(date_fin_str, '%Y-%m-%d').date()
    else:
        date_fin = timezone.now().date()
    
    if date_debut_str:
        date_debut = timezone.datetime.strptime(date_debut_str, '%Y-%m-%d').date()
    else:
        date_debut = date_fin - timedelta(days=30)
    
    rapport = RapportService.rapport_financier(date_debut, date_fin)
    
    context = {
        'title': 'Rapport Financier',
        'rapport': rapport,
        'date_debut': date_debut,
        'date_fin': date_fin,
    }
    
    # Rendre le template HTML
    html_string = render_to_string('reports/rapport_financier_pdf.html', context)
    
    # Créer la réponse HTTP
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="rapport_financier_{date_debut}_{date_fin}.pdf"'
    
    # Convertir HTML en PDF
    pisa.CreatePDF(html_string, dest=response)
    
    return response