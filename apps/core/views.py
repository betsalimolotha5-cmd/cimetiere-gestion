"""
Vues pour l'application core.
"""
from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from django.db.models import Q
import csv
from datetime import datetime
from django.core.management import call_command
from django.http import HttpResponse
from django.core.management import call_command
import os

def init_db(request):
    """Page temporaire pour initialiser la base de données"""
    result = []
    
    try:
        # 1. Migrations
        result.append("📦 Application des migrations...")
        call_command('migrate', verbosity=0)
        result.append("✅ Migrations appliquées")
        
        # 2. Fichiers statiques
        result.append("📁 Collecte des fichiers statiques...")
        call_command('collectstatic', verbosity=0, interactive=False)
        result.append("✅ Fichiers statiques collectés")
        
        # 3. Superutilisateur
        from apps.accounts.models import User
        admin_email = os.environ.get('ADMIN_EMAIL', 'betsalimolotha5@gmail.com')
        admin_password = os.environ.get('ADMIN_PASSWORD', '&Andrade2580')
        
        if not User.objects.filter(email=admin_email).exists():
            User.objects.create_superuser(
                email=admin_email,
                password=admin_password,
                first_name='Admin',
                last_name='Système',
            )
            result.append(f"✅ Superutilisateur créé: {admin_email}")
        else:
            result.append(f"⚠️ Superutilisateur existe déjà: {admin_email}")
        
        result.append("")
        result.append("🎉 INITIALISATION TERMINÉE !")
        result.append("<a href='/admin/'>👉 Aller à l'administration</a>")
        
    except Exception as e:
        result.append(f"❌ ERREUR: {str(e)}")
    
    html = "<br>".join(result)
    return HttpResponse(f"<h1>Initialisation</h1><p>{html}</p>")

def init_db(request):
    """Page temporaire pour initialiser la base de données"""
    try:
        call_command('migrate', verbosity=0)
        call_command('collectstatic', verbosity=0, interactive=False)
        
        # Créer le superutilisateur
        from apps.accounts.models import User
        import os
        admin_email = os.environ.get('ADMIN_EMAIL', 'betsalimolotha5@gmail.com')
        admin_password = os.environ.get('ADMIN_PASSWORD', '&Andrade2580')
        
        if not User.objects.filter(email=admin_email).exists():
            User.objects.create_superuser(
                email=admin_email,
                password=admin_password,
                first_name='Admin',
                last_name='Système',
            )
            message = f'✅ Base initialisée ! Superutilisateur créé: {admin_email}'
        else:
            message = f'✅ Base déjà initialisée. Superutilisateur: {admin_email}'
        
        return HttpResponse(f'<h1>{message}</h1><p><a href="/admin/">Aller à l\'admin</a></p>')
    except Exception as e:
        return HttpResponse(f'<h1>❌ Erreur</h1><pre>{str(e)}</pre>', status=500)

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

from .models import Zone, Caveau, Concession, Defunt, Inhumation, DemandeExhumation


@staff_member_required
def export_csv_caveaux(request):
    """Exporte la liste des caveaux en CSV."""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="caveaux_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    # BOM UTF-8 pour Excel
    response.write('\ufeff'.encode('utf-8'))
    
    writer = csv.writer(response, delimiter=';')
    writer.writerow([
        'Code',
        'Zone',
        'Statut',
        'Type',
        'Longueur (m)',
        'Largeur (m)',
        'Profondeur (m)',
        'Prix concession',
        'Prix perpétuité',
        'Rangée',
        'Numéro place',
        'Notes'
    ])
    
    caveaux = Caveau.objects.select_related('zone').all()
    for caveau in caveaux:
        writer.writerow([
            caveau.code,
            caveau.zone.nom if caveau.zone else '',
            caveau.get_statut_display(),
            caveau.get_type_caveau_display(),
            caveau.longueur,
            caveau.largeur,
            caveau.profondeur,
            caveau.prix_concession,
            caveau.prix_perpetuite,
            caveau.rangee,
            caveau.numero_place,
            caveau.notes
        ])
    
    return response


@staff_member_required
def export_csv_concessions(request):
    """Exporte la liste des concessions en CSV."""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="concessions_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    response.write('\ufeff'.encode('utf-8'))
    
    writer = csv.writer(response, delimiter=';')
    writer.writerow([
        'N° Contrat',
        'Concessionnaire',
        'Email',
        'Caveau',
        'Zone',
        'Type',
        'Durée (années)',
        'Date début',
        'Date fin',
        'Statut',
        'Montant total',
        'Montant payé',
        'Défunt',
        'Notes'
    ])
    
    concessions = Concession.objects.select_related('concessionnaire', 'caveau', 'caveau__zone', 'defunt').all()
    for concession in concessions:
        writer.writerow([
            concession.numero_contrat,
            concession.concessionnaire.get_full_name() if concession.concessionnaire else '',
            concession.concessionnaire.email if concession.concessionnaire else '',
            concession.caveau.code if concession.caveau else '',
            concession.caveau.zone.nom if concession.caveau and concession.caveau.zone else '',
            concession.get_type_concession_display(),
            concession.duree_annees or '',
            concession.date_debut.strftime('%d/%m/%Y') if concession.date_debut else '',
            concession.date_fin.strftime('%d/%m/%Y') if concession.date_fin else '',
            concession.get_statut_display(),
            concession.montant_total,
            concession.montant_paye,
            f"{concession.defunt.nom} {concession.defunt.prenom}" if concession.defunt else '',
            concession.notes
        ])
    
    return response


@staff_member_required
def export_csv_defunts(request):
    """Exporte la liste des défunts en CSV."""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="defunts_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    response.write('\ufeff'.encode('utf-8'))
    
    writer = csv.writer(response, delimiter=';')
    writer.writerow([
        'Nom',
        'Prénom',
        'Date naissance',
        'Date décès',
        'Lieu décès',
        'Sexe',
        'N° Identité',
        'Nationalité',
        'N° Acte décès',
        'Caveau',
        'Zone',
        'Notes'
    ])
    
    defunts = Defunt.objects.all()
    for defunt in defunts:
        caveau = ''
        zone = ''
        if defunt.concessions.exists():
            concession = defunt.concessions.first()
            if concession.caveau:
                caveau = concession.caveau.code
                if concession.caveau.zone:
                    zone = concession.caveau.zone.nom
        
        writer.writerow([
            defunt.nom,
            defunt.prenom,
            defunt.date_naissance.strftime('%d/%m/%Y') if defunt.date_naissance else '',
            defunt.date_deces.strftime('%d/%m/%Y') if defunt.date_deces else '',
            defunt.lieu_deces,
            defunt.get_sexe_display(),
            defunt.numero_identite,
            defunt.nationalite,
            defunt.numero_acte_deces,
            caveau,
            zone,
            defunt.notes
        ])
    
    return response


@staff_member_required
def export_csv_inhumations(request):
    """Exporte la liste des inhumations en CSV."""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="inhumations_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    response.write('\ufeff'.encode('utf-8'))
    
    writer = csv.writer(response, delimiter=';')
    writer.writerow([
        'Défunt',
        'Caveau',
        'Zone',
        'Date inhumation',
        'Profondeur (m)',
        'N° place dans caveau',
        'Notes'
    ])
    
    inhumations = Inhumation.objects.select_related('defunt', 'concession', 'concession__caveau', 'concession__caveau__zone').all()
    for inhumation in inhumations:
        writer.writerow([
            f"{inhumation.defunt.nom} {inhumation.defunt.prenom}",
            inhumation.concession.caveau.code if inhumation.concession.caveau else '',
            inhumation.concession.caveau.zone.nom if inhumation.concession.caveau and inhumation.concession.caveau.zone else '',
            inhumation.date_inhumation.strftime('%d/%m/%Y') if inhumation.date_inhumation else '',
            inhumation.profondeur,
            inhumation.numero_place_dans_caveau,
            inhumation.notes
        ])
    
    return response


@staff_member_required
def export_csv_exhumations(request):
    """Exporte la liste des demandes d'exhumation en CSV."""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="exhumations_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    response.write('\ufeff'.encode('utf-8'))
    
    writer = csv.writer(response, delimiter=';')
    writer.writerow([
        'ID',
        'Demandeur',
        'Lien parenté',
        'Téléphone',
        'Défunt',
        'Caveau',
        'Motif',
        'Destination',
        'Statut',
        'Date demande',
        'Date validation',
        'Date réalisation',
        'Notes'
    ])
    
    demandes = DemandeExhumation.objects.select_related('inhumation', 'inhumation__defunt', 'inhumation__concession', 'inhumation__concession__caveau').all()
    for demande in demandes:
        writer.writerow([
            demande.id,
            demande.nom_demandeur,
            demande.lien_parente,
            demande.telephone_demandeur,
            f"{demande.inhumation.defunt.nom} {demande.inhumation.defunt.prenom}" if demande.inhumation.defunt else '',
            demande.inhumation.concession.caveau.code if demande.inhumation.concession.caveau else '',
            demande.motif,
            demande.get_destination_display(),
            demande.get_statut_display(),
            demande.date_demande.strftime('%d/%m/%Y %H:%M') if demande.date_demande else '',
            demande.date_validation.strftime('%d/%m/%Y %H:%M') if demande.date_validation else '',
            demande.date_realisation.strftime('%d/%m/%Y %H:%M') if demande.date_realisation else '',
            demande.notes
        ])
    
    return response


@staff_member_required
def export_excel_caveaux(request):
    """Exporte la liste des caveaux en Excel."""
    if not EXCEL_AVAILABLE:
        return HttpResponse("La bibliothèque openpyxl n'est pas installée. Installez-la avec: pip install openpyxl")
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Caveaux"
    
    # En-têtes
    headers = ['Code', 'Zone', 'Statut', 'Type', 'Longueur (m)', 'Largeur (m)', 'Profondeur (m)', 'Prix concession', 'Prix perpétuité', 'Rangée', 'Numéro place', 'Notes']
    ws.append(headers)
    
    # Style des en-têtes
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")
    
    # Données
    caveaux = Caveau.objects.select_related('zone').all()
    for caveau in caveaux:
        ws.append([
            caveau.code,
            caveau.zone.nom if caveau.zone else '',
            caveau.get_statut_display(),
            caveau.get_type_caveau_display(),
            float(caveau.longueur),
            float(caveau.largeur),
            float(caveau.profondeur),
            float(caveau.prix_concession),
            float(caveau.prix_perpetuite),
            caveau.rangee,
            caveau.numero_place,
            caveau.notes
        ])
    
    # Ajuster les colonnes
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column_letter].width = adjusted_width
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="caveaux_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
    wb.save(response)
    
    return response


@staff_member_required
def export_excel_concessions(request):
    """Exporte la liste des concessions en Excel."""
    if not EXCEL_AVAILABLE:
        return HttpResponse("La bibliothèque openpyxl n'est pas installée. Installez-la avec: pip install openpyxl")
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Concessions"
    
    headers = ['N° Contrat', 'Concessionnaire', 'Email', 'Caveau', 'Zone', 'Type', 'Durée (années)', 'Date début', 'Date fin', 'Statut', 'Montant total', 'Montant payé', 'Défunt', 'Notes']
    ws.append(headers)
    
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")
    
    concessions = Concession.objects.select_related('concessionnaire', 'caveau', 'caveau__zone', 'defunt').all()
    for concession in concessions:
        ws.append([
            concession.numero_contrat,
            concession.concessionnaire.get_full_name() if concession.concessionnaire else '',
            concession.concessionnaire.email if concession.concessionnaire else '',
            concession.caveau.code if concession.caveau else '',
            concession.caveau.zone.nom if concession.caveau and concession.caveau.zone else '',
            concession.get_type_concession_display(),
            concession.duree_annees or '',
            concession.date_debut.strftime('%d/%m/%Y') if concession.date_debut else '',
            concession.date_fin.strftime('%d/%m/%Y') if concession.date_fin else '',
            concession.get_statut_display(),
            float(concession.montant_total),
            float(concession.montant_paye),
            f"{concession.defunt.nom} {concession.defunt.prenom}" if concession.defunt else '',
            concession.notes
        ])
    
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column_letter].width = adjusted_width
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="concessions_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
    wb.save(response)
    
    return response


@staff_member_required
def export_excel_defunts(request):
    """Exporte la liste des défunts en Excel."""
    if not EXCEL_AVAILABLE:
        return HttpResponse("La bibliothèque openpyxl n'est pas installée. Installez-la avec: pip install openpyxl")
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Défunts"
    
    headers = ['Nom', 'Prénom', 'Date naissance', 'Date décès', 'Lieu décès', 'Sexe', 'N° Identité', 'Nationalité', 'N° Acte décès', 'Caveau', 'Zone', 'Notes']
    ws.append(headers)
    
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")
    
    defunts = Defunt.objects.all()
    for defunt in defunts:
        caveau = ''
        zone = ''
        if defunt.concessions.exists():
            concession = defunt.concessions.first()
            if concession.caveau:
                caveau = concession.caveau.code
                if concession.caveau.zone:
                    zone = concession.caveau.zone.nom
        
        ws.append([
            defunt.nom,
            defunt.prenom,
            defunt.date_naissance.strftime('%d/%m/%Y') if defunt.date_naissance else '',
            defunt.date_deces.strftime('%d/%m/%Y') if defunt.date_deces else '',
            defunt.lieu_deces,
            defunt.get_sexe_display(),
            defunt.numero_identite,
            defunt.nationalite,
            defunt.numero_acte_deces,
            caveau,
            zone,
            defunt.notes
        ])
    
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column_letter].width = adjusted_width
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="defunts_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
    wb.save(response)
    
    return response


@staff_member_required
def export_excel_inhumations(request):
    """Exporte la liste des inhumations en Excel."""
    if not EXCEL_AVAILABLE:
        return HttpResponse("La bibliothèque openpyxl n'est pas installée. Installez-la avec: pip install openpyxl")
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Inhumations"
    
    headers = ['Défunt', 'Caveau', 'Zone', 'Date inhumation', 'Profondeur (m)', 'N° place dans caveau', 'Notes']
    ws.append(headers)
    
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")
    
    inhumations = Inhumation.objects.select_related('defunt', 'concession', 'concession__caveau', 'concession__caveau__zone').all()
    for inhumation in inhumations:
        ws.append([
            f"{inhumation.defunt.nom} {inhumation.defunt.prenom}",
            inhumation.concession.caveau.code if inhumation.concession.caveau else '',
            inhumation.concession.caveau.zone.nom if inhumation.concession.caveau and inhumation.concession.caveau.zone else '',
            inhumation.date_inhumation.strftime('%d/%m/%Y') if inhumation.date_inhumation else '',
            float(inhumation.profondeur),
            inhumation.numero_place_dans_caveau,
            inhumation.notes
        ])
    
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column_letter].width = adjusted_width
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="inhumations_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
    wb.save(response)
    
    return response


@staff_member_required
def export_excel_exhumations(request):
    """Exporte la liste des demandes d'exhumation en Excel."""
    if not EXCEL_AVAILABLE:
        return HttpResponse("La bibliothèque openpyxl n'est pas installée. Installez-la avec: pip install openpyxl")
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Exhumations"
    
    headers = ['ID', 'Demandeur', 'Lien parenté', 'Téléphone', 'Défunt', 'Caveau', 'Motif', 'Destination', 'Statut', 'Date demande', 'Date validation', 'Date réalisation', 'Notes']
    ws.append(headers)
    
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")
    
    demandes = DemandeExhumation.objects.select_related('inhumation', 'inhumation__defunt', 'inhumation__concession', 'inhumation__concession__caveau').all()
    for demande in demandes:
        ws.append([
            demande.id,
            demande.nom_demandeur,
            demande.lien_parente,
            demande.telephone_demandeur,
            f"{demande.inhumation.defunt.nom} {demande.inhumation.defunt.prenom}" if demande.inhumation.defunt else '',
            demande.inhumation.concession.caveau.code if demande.inhumation.concession.caveau else '',
            demande.motif,
            demande.get_destination_display(),
            demande.get_statut_display(),
            demande.date_demande.strftime('%d/%m/%Y %H:%M') if demande.date_demande else '',
            demande.date_validation.strftime('%d/%m/%Y %H:%M') if demande.date_validation else '',
            demande.date_realisation.strftime('%d/%m/%Y %H:%M') if demande.date_realisation else '',
            demande.notes
        ])
    
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column_letter].width = adjusted_width
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="exhumations_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
    wb.save(response)
    
    return response



@staff_member_required
def configurer_cimetiere(request):
    """Vue pour configurer les paramètres du cimetière."""
    from django.shortcuts import render, redirect
    from django.contrib import messages
    from .models import ParametreCimetiere
    from .forms import ParametreCimetiereForm
    
    # Récupérer ou créer les paramètres
    parametres = ParametreCimetiere.objects.first()
    
    if request.method == 'POST':
        if parametres:
            form = ParametreCimetiereForm(request.POST, instance=parametres)
        else:
            form = ParametreCimetiereForm(request.POST)
        
        if form.is_valid():
            form.save()
            messages.success(request, '✓ Paramètres du cimetière enregistrés avec succès.')
            return redirect('configurer_cimetiere')
    else:
        if parametres:
            form = ParametreCimetiereForm(instance=parametres)
        else:
            form = ParametreCimetiereForm()
    
    # Calculer les statistiques
    from .models import Zone, Caveau
    total_zones = Zone.objects.count()
    total_caveaux = Caveau.objects.count()
    caveaux_disponibles = Caveau.objects.filter(statut='DISPONIBLE').count()
    
    # Calculer la capacité théorique
    capacite_theorique = 0
    if parametres and parametres.superficie_totale > 0:
        surface_caveau = (parametres.longueur_standard_caveau * parametres.largeur_standard_caveau) + (parametres.largeur_allee * parametres.longueur_standard_caveau)
        if surface_caveau > 0:
            capacite_theorique = int(parametres.superficie_totale / surface_caveau)
    
    context = {
        'title': '⚙️ Configuration du Cimetière',
        'form': form,
        'parametres': parametres,
        'total_zones': total_zones,
        'total_caveaux': total_caveaux,
        'caveaux_disponibles': caveaux_disponibles,
        'capacite_theorique': capacite_theorique,
    }
    
    return render(request, 'core/configurer_cimetiere.html', context)