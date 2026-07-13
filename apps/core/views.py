"""
Vues pour l'application core.
"""
from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from django.db.models import Q
import csv
import os
from datetime import datetime
from django.core.management import call_command

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

from .models import Zone, Caveau, Concession, Defunt, Inhumation, DemandeExhumation


# ==============================================================================
# INITIALISATION DE LA BASE DE DONNÉES (Pour le déploiement)
# ==============================================================================
def init_db(request):
    """Page temporaire pour initialiser la base de données en production"""
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
            result.append(f"✅ Superutilisateur créé : {admin_email}")
        else:
            result.append(f"⚠️ Superutilisateur existe déjà : {admin_email}")
        
        result.append("<br><br>🎉 <b>INITIALISATION TERMINÉE AVEC SUCCÈS !</b>")
        result.append("<a href='/admin/' style='font-size: 1.2em; color: blue;'>👉 Aller à l'administration</a>")
        
    except Exception as e:
        result.append(f"<br><br>❌ <b>ERREUR :</b> {str(e)}")
    
    html = "<br>".join(result)
    return HttpResponse(f"<h1>Initialisation de la base de données</h1><p>{html}</p>")


# ==============================================================================
# EXPORTS CSV
# ==============================================================================
@staff_member_required
def export_csv_caveaux(request):
    """Exporte la liste des caveaux en CSV."""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="caveaux_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    response.write('\ufeff'.encode('utf-8'))
    
    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Code', 'Zone', 'Statut', 'Type', 'Longueur (m)', 'Largeur (m)', 'Profondeur (m)', 'Prix concession', 'Prix perpétuité', 'Rangée', 'Numéro place', 'Notes'])
    
    for caveau in Caveau.objects.select_related('zone').all():
        writer.writerow([
            caveau.code, caveau.zone.nom if caveau.zone else '', caveau.get_statut_display(),
            caveau.get_type_caveau_display(), caveau.longueur, caveau.largeur, caveau.profondeur,
            caveau.prix_concession, caveau.prix_perpetuite, caveau.rangee, caveau.numero_place, caveau.notes
        ])
    return response


@staff_member_required
def export_csv_concessions(request):
    """Exporte la liste des concessions en CSV."""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="concessions_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    response.write('\ufeff'.encode('utf-8'))
    
    writer = csv.writer(response, delimiter=';')
    writer.writerow(['N° Contrat', 'Concessionnaire', 'Email', 'Caveau', 'Zone', 'Type', 'Durée (années)', 'Date début', 'Date fin', 'Statut', 'Montant total', 'Montant payé', 'Défunt', 'Notes'])
    
    for c in Concession.objects.select_related('concessionnaire', 'caveau', 'caveau__zone', 'defunt').all():
        writer.writerow([
            c.numero_contrat, c.concessionnaire.get_full_name() if c.concessionnaire else '',
            c.concessionnaire.email if c.concessionnaire else '', c.caveau.code if c.caveau else '',
            c.caveau.zone.nom if c.caveau and c.caveau.zone else '', c.get_type_concession_display(),
            c.duree_annees or '', c.date_debut.strftime('%d/%m/%Y') if c.date_debut else '',
            c.date_fin.strftime('%d/%m/%Y') if c.date_fin else '', c.get_statut_display(),
            c.montant_total, c.montant_paye, f"{c.defunt.nom} {c.defunt.prenom}" if c.defunt else '', c.notes
        ])
    return response


@staff_member_required
def export_csv_defunts(request):
    """Exporte la liste des défunts en CSV."""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="defunts_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    response.write('\ufeff'.encode('utf-8'))
    
    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Nom', 'Prénom', 'Date naissance', 'Date décès', 'Lieu décès', 'Sexe', 'N° Identité', 'Nationalité', 'N° Acte décès', 'Caveau', 'Zone', 'Notes'])
    
    for defunt in Defunt.objects.all():
        caveau, zone = '', ''
        if defunt.concessions.exists():
            concession = defunt.concessions.first()
            if concession.caveau:
                caveau = concession.caveau.code
                zone = concession.caveau.zone.nom if concession.caveau.zone else ''
        
        writer.writerow([
            defunt.nom, defunt.prenom, defunt.date_naissance.strftime('%d/%m/%Y') if defunt.date_naissance else '',
            defunt.date_deces.strftime('%d/%m/%Y') if defunt.date_deces else '', defunt.lieu_deces,
            defunt.get_sexe_display(), defunt.numero_identite, defunt.nationalite, defunt.numero_acte_deces, caveau, zone, defunt.notes
        ])
    return response


@staff_member_required
def export_csv_inhumations(request):
    """Exporte la liste des inhumations en CSV."""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="inhumations_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    response.write('\ufeff'.encode('utf-8'))
    
    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Défunt', 'Caveau', 'Zone', 'Date inhumation', 'Profondeur (m)', 'N° place dans caveau', 'Notes'])
    
    for inh in Inhumation.objects.select_related('defunt', 'concession', 'concession__caveau', 'concession__caveau__zone').all():
        writer.writerow([
            f"{inh.defunt.nom} {inh.defunt.prenom}",
            inh.concession.caveau.code if inh.concession.caveau else '',
            inh.concession.caveau.zone.nom if inh.concession.caveau and inh.concession.caveau.zone else '',
            inh.date_inhumation.strftime('%d/%m/%Y') if inh.date_inhumation else '',
            inh.profondeur, inh.numero_place_dans_caveau, inh.notes
        ])
    return response


@staff_member_required
def export_csv_exhumations(request):
    """Exporte la liste des demandes d'exhumation en CSV."""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="exhumations_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    response.write('\ufeff'.encode('utf-8'))
    
    writer = csv.writer(response, delimiter=';')
    writer.writerow(['ID', 'Demandeur', 'Lien parenté', 'Téléphone', 'Défunt', 'Caveau', 'Motif', 'Destination', 'Statut', 'Date demande', 'Date validation', 'Date réalisation', 'Notes'])
    
    for demande in DemandeExhumation.objects.select_related('inhumation', 'inhumation__defunt', 'inhumation__concession', 'inhumation__concession__caveau').all():
        writer.writerow([
            demande.id, demande.nom_demandeur, demande.lien_parente, demande.telephone_demandeur,
            f"{demande.inhumation.defunt.nom} {demande.inhumation.defunt.prenom}" if demande.inhumation.defunt else '',
            demande.inhumation.concession.caveau.code if demande.inhumation.concession.caveau else '',
            demande.motif, demande.get_destination_display(), demande.get_statut_display(),
            demande.date_demande.strftime('%d/%m/%Y %H:%M') if demande.date_demande else '',
            demande.date_validation.strftime('%d/%m/%Y %H:%M') if demande.date_validation else '',
            demande.date_realisation.strftime('%d/%m/%Y %H:%M') if demande.date_realisation else '', demande.notes
        ])
    return response


# ==============================================================================
# EXPORTS EXCEL
# ==============================================================================
@staff_member_required
def export_excel_caveaux(request):
    if not EXCEL_AVAILABLE:
        return HttpResponse("La bibliothèque openpyxl n'est pas installée.")
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Caveaux"
    headers = ['Code', 'Zone', 'Statut', 'Type', 'Longueur (m)', 'Largeur (m)', 'Profondeur (m)', 'Prix concession', 'Prix perpétuité', 'Rangée', 'Numéro place', 'Notes']
    ws.append(headers)
    
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    for cell in ws[1]:
        cell.fill, cell.font, cell.alignment = header_fill, header_font, Alignment(horizontal="center")
    
    for caveau in Caveau.objects.select_related('zone').all():
        ws.append([caveau.code, caveau.zone.nom if caveau.zone else '', caveau.get_statut_display(), caveau.get_type_caveau_display(), float(caveau.longueur), float(caveau.largeur), float(caveau.profondeur), float(caveau.prix_concession), float(caveau.prix_perpetuite), caveau.rangee, caveau.numero_place, caveau.notes])
    
    for column in ws.columns:
        max_length = max((len(str(cell.value)) for cell in column if cell.value), default=0)
        ws.column_dimensions[column[0].column_letter].width = min(max_length + 2, 50)
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="caveaux_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
    wb.save(response)
    return response


@staff_member_required
def export_excel_concessions(request):
    if not EXCEL_AVAILABLE:
        return HttpResponse("La bibliothèque openpyxl n'est pas installée.")
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Concessions"
    headers = ['N° Contrat', 'Concessionnaire', 'Email', 'Caveau', 'Zone', 'Type', 'Durée (années)', 'Date début', 'Date fin', 'Statut', 'Montant total', 'Montant payé', 'Défunt', 'Notes']
    ws.append(headers)
    
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    for cell in ws[1]:
        cell.fill, cell.font, cell.alignment = header_fill, header_font, Alignment(horizontal="center")
    
    for c in Concession.objects.select_related('concessionnaire', 'caveau', 'caveau__zone', 'defunt').all():
        ws.append([c.numero_contrat, c.concessionnaire.get_full_name() if c.concessionnaire else '', c.concessionnaire.email if c.concessionnaire else '', c.caveau.code if c.caveau else '', c.caveau.zone.nom if c.caveau and c.caveau.zone else '', c.get_type_concession_display(), c.duree_annees or '', c.date_debut.strftime('%d/%m/%Y') if c.date_debut else '', c.date_fin.strftime('%d/%m/%Y') if c.date_fin else '', c.get_statut_display(), float(c.montant_total), float(c.montant_paye), f"{c.defunt.nom} {c.defunt.prenom}" if c.defunt else '', c.notes])
    
    for column in ws.columns:
        max_length = max((len(str(cell.value)) for cell in column if cell.value), default=0)
        ws.column_dimensions[column[0].column_letter].width = min(max_length + 2, 50)
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="concessions_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
    wb.save(response)
    return response


@staff_member_required
def export_excel_defunts(request):
    if not EXCEL_AVAILABLE:
        return HttpResponse("La bibliothèque openpyxl n'est pas installée.")
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Défunts"
    headers = ['Nom', 'Prénom', 'Date naissance', 'Date décès', 'Lieu décès', 'Sexe', 'N° Identité', 'Nationalité', 'N° Acte décès', 'Caveau', 'Zone', 'Notes']
    ws.append(headers)
    
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    for cell in ws[1]:
        cell.fill, cell.font, cell.alignment = header_fill, header_font, Alignment(horizontal="center")
    
    for defunt in Defunt.objects.all():
        caveau, zone = '', ''
        if defunt.concessions.exists():
            concession = defunt.concessions.first()
            if concession.caveau:
                caveau = concession.caveau.code
                zone = concession.caveau.zone.nom if concession.caveau.zone else ''
        ws.append([defunt.nom, defunt.prenom, defunt.date_naissance.strftime('%d/%m/%Y') if defunt.date_naissance else '', defunt.date_deces.strftime('%d/%m/%Y') if defunt.date_deces else '', defunt.lieu_deces, defunt.get_sexe_display(), defunt.numero_identite, defunt.nationalite, defunt.numero_acte_deces, caveau, zone, defunt.notes])
    
    for column in ws.columns:
        max_length = max((len(str(cell.value)) for cell in column if cell.value), default=0)
        ws.column_dimensions[column[0].column_letter].width = min(max_length + 2, 50)
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="defunts_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
    wb.save(response)
    return response


@staff_member_required
def export_excel_inhumations(request):
    if not EXCEL_AVAILABLE:
        return HttpResponse("La bibliothèque openpyxl n'est pas installée.")
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Inhumations"
    headers = ['Défunt', 'Caveau', 'Zone', 'Date inhumation', 'Profondeur (m)', 'N° place dans caveau', 'Notes']
    ws.append(headers)
    
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    for cell in ws[1]:
        cell.fill, cell.font, cell.alignment = header_fill, header_font, Alignment(horizontal="center")
    
    for inh in Inhumation.objects.select_related('defunt', 'concession', 'concession__caveau', 'concession__caveau__zone').all():
        ws.append([f"{inh.defunt.nom} {inh.defunt.prenom}", inh.concession.caveau.code if inh.concession.caveau else '', inh.concession.caveau.zone.nom if inh.concession.caveau and inh.concession.caveau.zone else '', inh.date_inhumation.strftime('%d/%m/%Y') if inh.date_inhumation else '', float(inh.profondeur), inh.numero_place_dans_caveau, inh.notes])
    
    for column in ws.columns:
        max_length = max((len(str(cell.value)) for cell in column if cell.value), default=0)
        ws.column_dimensions[column[0].column_letter].width = min(max_length + 2, 50)
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="inhumations_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
    wb.save(response)
    return response


@staff_member_required
def export_excel_exhumations(request):
    if not EXCEL_AVAILABLE:
        return HttpResponse("La bibliothèque openpyxl n'est pas installée.")
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Exhumations"
    headers = ['ID', 'Demandeur', 'Lien parenté', 'Téléphone', 'Défunt', 'Caveau', 'Motif', 'Destination', 'Statut', 'Date demande', 'Date validation', 'Date réalisation', 'Notes']
    ws.append(headers)
    
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    for cell in ws[1]:
        cell.fill, cell.font, cell.alignment = header_fill, header_font, Alignment(horizontal="center")
    
    for demande in DemandeExhumation.objects.select_related('inhumation', 'inhumation__defunt', 'inhumation__concession', 'inhumation__concession__caveau').all():
        ws.append([demande.id, demande.nom_demandeur, demande.lien_parente, demande.telephone_demandeur, f"{demande.inhumation.defunt.nom} {demande.inhumation.defunt.prenom}" if demande.inhumation.defunt else '', demande.inhumation.concession.caveau.code if demande.inhumation.concession.caveau else '', demande.motif, demande.get_destination_display(), demande.get_statut_display(), demande.date_demande.strftime('%d/%m/%Y %H:%M') if demande.date_demande else '', demande.date_validation.strftime('%d/%m/%Y %H:%M') if demande.date_validation else '', demande.date_realisation.strftime('%d/%m/%Y %H:%M') if demande.date_realisation else '', demande.notes])
    
    for column in ws.columns:
        max_length = max((len(str(cell.value)) for cell in column if cell.value), default=0)
        ws.column_dimensions[column[0].column_letter].width = min(max_length + 2, 50)
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="exhumations_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
    wb.save(response)
    return response


# ==============================================================================
# CONFIGURATION
# ==============================================================================
@staff_member_required
def configurer_cimetiere(request):
    """Vue pour configurer les paramètres du cimetière."""
    from django.contrib import messages
    from .models import ParametreCimetiere
    from .forms import ParametreCimetiereForm
    
    parametres = ParametreCimetiere.objects.first()
    
    if request.method == 'POST':
        form = ParametreCimetiereForm(request.POST, instance=parametres) if parametres else ParametreCimetiereForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '✓ Paramètres du cimetière enregistrés avec succès.')
            return redirect('configurer_cimetiere')
    else:
        form = ParametreCimetiereForm(instance=parametres) if parametres else ParametreCimetiereForm()
    
    total_zones = Zone.objects.count()
    total_caveaux = Caveau.objects.count()
    caveaux_disponibles = Caveau.objects.filter(statut='DISPONIBLE').count()
    
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