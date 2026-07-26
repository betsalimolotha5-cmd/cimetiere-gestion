"""
Vues pour l'application core.
AJOUT : Génération de PDF pour le contrat, l'attestation, le PV d'inhumation, l'autorisation, le PV d'exhumation et le rapport statistique.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.db.models import Q, Sum, Count
from django.template.loader import get_template
from django.utils import timezone
from django.contrib import messages
import csv
import os
import calendar
from datetime import datetime
from django.core.management import call_command

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

from .models import Zone, Caveau, Concession, Defunt, Inhumation, DemandeExhumation, ParametreCimetiere


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
# EXPORTS PDF
# ==============================================================================
@login_required
def contrat_concession_pdf(request, concession_id):
    """Génère et télécharge le contrat de concession au format PDF."""
    if not WEASYPRINT_AVAILABLE:
        messages.error(request, "Le système de génération PDF n'est pas disponible. Contactez l'administrateur.")
        return redirect('admin:core_concession_changelist')
    
    if request.user.is_staff:
        concession = get_object_or_404(Concession, id=concession_id)
    else:
        concession = get_object_or_404(Concession, id=concession_id, concessionnaire=request.user)
    
    parametres = ParametreCimetiere.objects.first()
    context = {'concession': concession, 'parametres': parametres, 'date_generation': timezone.now(), 'site_name': 'Gestion Cimetière'}
    
    try:
        template = get_template('core/pdf/contrat_concession_pdf.html')
        pdf_file = HTML(string=template.render(context), base_url=request.build_absolute_uri('/')).write_pdf()
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="contrat_{concession.numero_contrat}.pdf"'
        return response
    except Exception as e:
        messages.error(request, f"Erreur lors de la génération du PDF : {str(e)}")
        return redirect('admin:core_concession_change', concession_id)


@login_required
def attestation_concession_pdf(request, concession_id):
    """Génère et télécharge l'attestation de concession au format PDF."""
    if not WEASYPRINT_AVAILABLE:
        messages.error(request, "Le système de génération PDF n'est pas disponible.")
        return redirect('admin:core_concession_changelist')
    
    if request.user.is_staff:
        concession = get_object_or_404(Concession, id=concession_id)
    else:
        concession = get_object_or_404(Concession, id=concession_id, concessionnaire=request.user)
    
    parametres = ParametreCimetiere.objects.first()
    context = {'concession': concession, 'parametres': parametres, 'date_generation': timezone.now(), 'site_name': 'Gestion Cimetière'}
    
    try:
        template = get_template('core/pdf/attestation_concession_pdf.html')
        pdf_file = HTML(string=template.render(context), base_url=request.build_absolute_uri('/')).write_pdf()
        nom_client = concession.concessionnaire.get_full_name().replace(' ', '_') if concession.concessionnaire.get_full_name() else 'Client'
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Attestation_{nom_client}_{timezone.now().strftime("%Y%m%d")}.pdf"'
        return response
    except Exception as e:
        messages.error(request, f"Erreur : {str(e)}")
        return redirect('admin:core_concession_change', concession_id)


@login_required
def pv_inhumation_pdf(request, inhumation_id):
    """Génère et télécharge le PV d'inhumation au format PDF."""
    if not WEASYPRINT_AVAILABLE or not request.user.is_staff:
        messages.error(request, "Accès réservé ou système PDF indisponible.")
        return redirect('admin:core_inhumation_changelist')
    
    inhumation = get_object_or_404(Inhumation, id=inhumation_id)
    parametres = ParametreCimetiere.objects.first()
    context = {'inhumation': inhumation, 'parametres': parametres, 'date_generation': timezone.now(), 'site_name': 'Gestion Cimetière'}
    
    try:
        template = get_template('core/pdf/pv_inhumation_pdf.html')
        pdf_file = HTML(string=template.render(context), base_url=request.build_absolute_uri('/')).write_pdf()
        nom_defunt = inhumation.defunt.nom.replace(' ', '_') if inhumation.defunt else 'Defunt'
        date_str = inhumation.date_inhumation.strftime('%Y%m%d') if inhumation.date_inhumation else timezone.now().strftime('%Y%m%d')
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="PV_inhumation_{nom_defunt}_{date_str}.pdf"'
        return response
    except Exception as e:
        messages.error(request, f"Erreur : {str(e)}")
        return redirect('admin:core_inhumation_change', inhumation_id)


@login_required
def autorisation_exhumation_pdf(request, demande_id):
    """Génère et télécharge l'autorisation d'exhumation au format PDF."""
    if not WEASYPRINT_AVAILABLE or not request.user.is_staff:
        messages.error(request, "Accès réservé ou système PDF indisponible.")
        return redirect('admin:core_demandeexhumation_changelist')
    
    demande = get_object_or_404(DemandeExhumation, id=demande_id)
    parametres = ParametreCimetiere.objects.first()
    context = {'demande': demande, 'parametres': parametres, 'date_generation': timezone.now(), 'site_name': 'Gestion Cimetière'}
    
    try:
        template = get_template('core/pdf/autorisation_exhumation_pdf.html')
        pdf_file = HTML(string=template.render(context), base_url=request.build_absolute_uri('/')).write_pdf()
        nom_defunt = demande.inhumation.defunt.nom.replace(' ', '_') if demande.inhumation and demande.inhumation.defunt else 'Defunt'
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Autorisation_exhumation_{nom_defunt}_{timezone.now().strftime("%Y%m%d")}.pdf"'
        return response
    except Exception as e:
        messages.error(request, f"Erreur : {str(e)}")
        return redirect('admin:core_demandeexhumation_change', demande_id)


@login_required
def pv_exhumation_pdf(request, demande_id):
    """Génère et télécharge le PV d'exhumation au format PDF."""
    if not WEASYPRINT_AVAILABLE or not request.user.is_staff:
        messages.error(request, "Accès réservé ou système PDF indisponible.")
        return redirect('admin:core_demandeexhumation_changelist')
    
    demande = get_object_or_404(DemandeExhumation, id=demande_id)
    parametres = ParametreCimetiere.objects.first()
    context = {'demande': demande, 'parametres': parametres, 'date_generation': timezone.now(), 'site_name': 'Gestion Cimetière'}
    
    try:
        template = get_template('core/pdf/pv_exhumation_pdf.html')
        pdf_file = HTML(string=template.render(context), base_url=request.build_absolute_uri('/')).write_pdf()
        nom_defunt = demande.inhumation.defunt.nom.replace(' ', '_') if demande.inhumation and demande.inhumation.defunt else 'Defunt'
        date_str = demande.date_realisation.strftime('%Y%m%d') if demande.date_realisation else timezone.now().strftime('%Y%m%d')
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="PV_exhumation_{nom_defunt}_{date_str}.pdf"'
        return response
    except Exception as e:
        messages.error(request, f"Erreur : {str(e)}")
        return redirect('admin:core_demandeexhumation_change', demande_id)


@staff_member_required
def rapport_statistique_pdf(request):
    """Génère et télécharge le rapport statistique global du cimetière."""
    if not WEASYPRINT_AVAILABLE:
        messages.error(request, "Le système de génération PDF n'est pas disponible.")
        return redirect('admin:index')
    
    # 1. Gestion des dates (par défaut : mois en cours)
    debut_str = request.GET.get('debut')
    fin_str = request.GET.get('fin')
    
    if debut_str and fin_str:
        try:
            date_debut = datetime.strptime(debut_str, '%Y-%m-%d').date()
            date_fin = datetime.strptime(fin_str, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, "Format de date invalide. Utilisez AAAA-MM-JJ.")
            return redirect('admin:index')
    else:
        today = timezone.now().date()
        date_debut = today.replace(day=1)
        _, last_day = calendar.monthrange(today.year, today.month)
        date_fin = today.replace(day=last_day)
    
    # 2. Agrégation des données
    total_caveaux = Caveau.objects.count()
    caveaux_disponibles = Caveau.objects.filter(statut='DISPONIBLE').count()
    caveaux_occupes = Caveau.objects.filter(statut='OCCUPE').count()
    taux_occupation = round((caveaux_occupes / total_caveaux * 100), 1) if total_caveaux > 0 else 0
    
    total_concessions = Concession.objects.count()
    concessions_actives = Concession.objects.filter(statut='ACTIVE').count()
    
    inhumations_periode = Inhumation.objects.filter(date_inhumation__range=(date_debut, date_fin)).count()
    exhumations_periode = DemandeExhumation.objects.filter(date_realisation__range=(date_debut, date_fin)).count()
    
    # Revenus (Import dynamique pour éviter les problèmes de circularité)
    try:
        from apps.billing.models import Paiement
        revenus = Paiement.objects.filter(
            statut='VALIDE', 
            date_paiement__range=(date_debut, date_fin)
        ).aggregate(total=Sum('montant'))['total'] or 0
    except Exception:
        revenus = 0  # Fallback si l'app billing n'est pas encore totalement liée
    
    parametres = ParametreCimetiere.objects.first()
    
    context = {
        'date_debut': date_debut,
        'date_fin': date_fin,
        'total_caveaux': total_caveaux,
        'caveaux_disponibles': caveaux_disponibles,
        'caveaux_occupes': caveaux_occupes,
        'taux_occupation': taux_occupation,
        'total_concessions': total_concessions,
        'concessions_actives': concessions_actives,
        'inhumations_periode': inhumations_periode,
        'exhumations_periode': exhumations_periode,
        'revenus_periode': revenus,
        'parametres': parametres,
        'date_generation': timezone.now(),
    }
    
    try:
        template = get_template('core/pdf/rapport_statistique_pdf.html')
        html_content = template.render(context)
        pdf_file = HTML(string=html_content, base_url=request.build_absolute_uri('/')).write_pdf()
        
        filename = f"Rapport_Statistique_{date_debut.strftime('%Y%m')}_a_{date_fin.strftime('%Y%m%d')}.pdf"
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except Exception as e:
        messages.error(request, f"Erreur lors de la génération du rapport : {str(e)}")
        return redirect('admin:index')


# ==============================================================================
# CONFIGURATION
# ==============================================================================
@staff_member_required
def configurer_cimetiere(request):
    """Vue pour configurer les paramètres du cimetière."""
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