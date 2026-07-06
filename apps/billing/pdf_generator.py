"""
Générateur de factures PDF et documents d'exhumation avec ReportLab.
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas
from django.conf import settings
from io import BytesIO
from datetime import datetime
import os


def generer_facture_pdf(facture):
    """
    Génère un PDF pour une facture et le sauvegarde dans le dossier media.
    
    Args:
        facture: Instance du modèle Facture
        
    Returns:
        str: Chemin relatif du fichier PDF généré
    """
    now = datetime.now()
    relative_path = f'factures/pdf/{now.year}/{now.month:02d}/'
    full_path = os.path.join(settings.MEDIA_ROOT, relative_path)
    os.makedirs(full_path, exist_ok=True)
    
    filename = f'facture_{facture.numero_facture}.pdf'
    file_path = os.path.join(full_path, filename)
    
    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=30,
        alignment=1
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#34495e'),
        spaceAfter=12,
        spaceBefore=12
    )
    
    normal_style = styles['Normal']
    
    story = []
    
    story.append(Paragraph("FACTURE", title_style))
    story.append(Spacer(1, 0.5*cm))
    
    info_data = [
        ['N° de facture:', facture.numero_facture],
        ['Date d\'émission:', facture.date_emission.strftime('%d/%m/%Y')],
        ['Date d\'échéance:', facture.date_echeance.strftime('%d/%m/%Y')],
        ['Statut:', facture.get_statut_display()],
    ]
    
    info_table = Table(info_data, colWidths=[5*cm, 10*cm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2c3e50')),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    story.append(info_table)
    story.append(Spacer(1, 0.8*cm))
    
    story.append(Paragraph("CLIENT", heading_style))
    
    client_info = f"""
    <b>Nom:</b> {facture.client.get_full_name() or facture.client.email}<br/>
    <b>Email:</b> {facture.client.email}<br/>
    """
    if hasattr(facture.client, 'telephone') and facture.client.telephone:
        client_info += f"<b>Téléphone:</b> {facture.client.telephone}<br/>"
    
    story.append(Paragraph(client_info, normal_style))
    story.append(Spacer(1, 0.8*cm))
    
    story.append(Paragraph("CONCESSION", heading_style))
    
    concession = facture.concession
    caveau = concession.caveau
    
    concession_info = f"""
    <b>Caveau:</b> {caveau.code}<br/>
    <b>Zone:</b> {caveau.zone.nom if caveau.zone else 'Non définie'}<br/>
    <b>Type de concession:</b> {concession.get_type_concession_display()}<br/>
    <b>Durée:</b> {concession.duree_annees} an(s)<br/>
    """
    
    story.append(Paragraph(concession_info, normal_style))
    story.append(Spacer(1, 0.8*cm))
    
    if facture.description:
        story.append(Paragraph("DESCRIPTION", heading_style))
        story.append(Paragraph(facture.description, normal_style))
        story.append(Spacer(1, 0.8*cm))
    
    story.append(Paragraph("MONTANTS", heading_style))
    
    montant_data = [
        ['Montant HT:', f'{facture.montant_ht:,.2f} FCFA'],
        ['TVA:', f'{facture.taux_tva}%'],
        ['Montant TVA:', f'{facture.montant_tva:,.2f} FCFA'],
        ['', ''],
        ['TOTAL TTC:', f'{facture.montant_total:,.2f} FCFA'],
        ['', ''],
        ['Montant payé:', f'{facture.montant_paye:,.2f} FCFA'],
        ['Montant restant:', f'{facture.montant_restant:,.2f} FCFA'],
    ]
    
    montant_table = Table(montant_data, colWidths=[8*cm, 7*cm])
    montant_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2c3e50')),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LINEABOVE', (0, 3), (-1, 3), 1, colors.grey),
        ('LINEABOVE', (0, 5), (-1, 5), 1, colors.grey),
        ('FONTNAME', (0, 4), (-1, 4), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 4), (-1, 4), 12),
        ('TEXTCOLOR', (0, 4), (-1, 4), colors.HexColor('#e74c3c')),
    ]))
    
    story.append(montant_table)
    story.append(Spacer(1, 1*cm))
    
    if facture.notes:
        story.append(Paragraph("NOTES", heading_style))
        story.append(Paragraph(facture.notes, normal_style))
        story.append(Spacer(1, 0.8*cm))
    
    story.append(Spacer(1, 2*cm))
    footer_text = f"""
    <i>Cette facture a été générée automatiquement le {now.strftime('%d/%m/%Y à %H:%M')}<br/>
    Gestion du Cimetière - {settings.DEFAULT_FROM_EMAIL}</i>
    """
    story.append(Paragraph(footer_text, ParagraphStyle(
        'Footer',
        parent=normal_style,
        fontSize=8,
        textColor=colors.grey,
        alignment=1
    )))
    
    doc.build(story)
    
    return f'{relative_path}{filename}'


def envoyer_facture_par_email(facture):
    """
    Envoie la facture PDF par email au client.
    
    Args:
        facture: Instance du modèle Facture
        
    Returns:
        bool: True si l'email a été envoyé avec succès
    """
    from django.core.mail import EmailMessage
    
    if not facture.fichier_pdf:
        return False
    
    sujet = f'Votre facture {facture.numero_facture} - Gestion Cimetière'
    
    message_texte = f"""
    Bonjour {facture.client.get_full_name() or facture.client.email},
    
    Votre facture {facture.numero_facture} d'un montant de {facture.montant_total:,.2f} FCFA a été générée.
    
    Date d'émission: {facture.date_emission.strftime('%d/%m/%Y')}
    Date d'échéance: {facture.date_echeance.strftime('%d/%m/%Y')}
    Statut: {facture.get_statut_display()}
    
    Veuillez trouver la facture en pièce jointe de cet email.
    
    Pour toute question, n'hésitez pas à nous contacter.
    """
    
    message_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
        <div style="max-width: 600px; margin: auto; background: white; padding: 30px; border-radius: 10px;">
            <h2 style="color: #2c3e50;">📄 Votre facture est disponible</h2>
            <p>Bonjour <strong>{facture.client.get_full_name() or facture.client.email}</strong>,</p>
            <p>Votre facture <strong>{facture.numero_facture}</strong> d'un montant de 
               <strong>{facture.montant_total:,.2f} FCFA</strong> a été générée.</p>
            
            <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <p style="margin: 5px 0;"><strong>Date d'émission:</strong> {facture.date_emission.strftime('%d/%m/%Y')}</p>
                <p style="margin: 5px 0;"><strong>Date d'échéance:</strong> {facture.date_echeance.strftime('%d/%m/%Y')}</p>
                <p style="margin: 5px 0;"><strong>Statut:</strong> {facture.get_statut_display()}</p>
            </div>
            
            <p>Veuillez trouver la facture en pièce jointe de cet email.</p>
            
            <p style="margin-top: 30px; color: #7f8c8d; font-size: 12px;">
                Pour toute question, n'hésitez pas à nous contacter.
            </p>
        </div>
    </body>
    </html>
    """
    
    email = EmailMessage(
        subject=sujet,
        body=message_html,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[facture.client.email],
    )
    email.content_subtype = 'html'
    
    pdf_path = os.path.join(settings.MEDIA_ROOT, facture.fichier_pdf.name)
    if os.path.exists(pdf_path):
        with open(pdf_path, 'rb') as f:
            email.attach(f'facture_{facture.numero_facture}.pdf', f.read(), 'application/pdf')
    
    try:
        email.send(fail_silently=False)
        return True
    except Exception as e:
        print(f"Erreur envoi email facture: {e}")
        return False


def generer_autorisation_exhumation(demande):
    """
    Génère un PDF d'autorisation d'exhumation.
    
    Args:
        demande: Instance du modèle DemandeExhumation
        
    Returns:
        str: Chemin relatif du fichier PDF généré
    """
    now = datetime.now()
    relative_path = f'exhumations/autorisations/{now.year}/{now.month:02d}/'
    full_path = os.path.join(settings.MEDIA_ROOT, relative_path)
    os.makedirs(full_path, exist_ok=True)
    
    filename = f'autorisation_{demande.id}.pdf'
    file_path = os.path.join(full_path, filename)
    
    inhumation = demande.inhumation
    concession = inhumation.concession
    caveau = concession.caveau
    defunt = inhumation.defunt
    
    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=22,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=20,
        alignment=1
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#34495e'),
        spaceAfter=12,
        spaceBefore=12
    )
    
    normal_style = styles['Normal']
    
    story = []
    
    story.append(Paragraph("AUTORISATION D'EXHUMATION", title_style))
    story.append(Spacer(1, 0.5*cm))
    
    ref_data = [
        ['Référence:', f'EXH-{demande.id:05d}'],
        ['Date d\'autorisation:', now.strftime('%d/%m/%Y')],
        ['Date de la demande:', demande.date_demande.strftime('%d/%m/%Y') if demande.date_demande else '-'],
    ]
    
    ref_table = Table(ref_data, colWidths=[5*cm, 10*cm])
    ref_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2c3e50')),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    story.append(ref_table)
    story.append(Spacer(1, 0.8*cm))
    
    story.append(Paragraph("DÉFUNT CONCERNÉ", heading_style))
    
    defunt_info = f"""
    <b>Nom:</b> {defunt.nom if defunt else 'Non renseigné'}<br/>
    <b>Prénom:</b> {defunt.prenom if defunt else 'Non renseigné'}<br/>
    <b>Date de décès:</b> {defunt.date_deces.strftime('%d/%m/%Y') if defunt and defunt.date_deces else '-'}<br/>
    """
    
    story.append(Paragraph(defunt_info, normal_style))
    story.append(Spacer(1, 0.8*cm))
    
    story.append(Paragraph("CONCESSION CONCERNÉE", heading_style))
    
    concession_info = f"""
    <b>N° de contrat:</b> {concession.numero_contrat}<br/>
    <b>Caveau:</b> {caveau.code}<br/>
    <b>Zone:</b> {caveau.zone.nom if caveau.zone else 'Non définie'}<br/>
    <b>Concessionnaire:</b> {concession.concessionnaire.get_full_name() or concession.concessionnaire.email}<br/>
    """
    
    story.append(Paragraph(concession_info, normal_style))
    story.append(Spacer(1, 0.8*cm))
    
    story.append(Paragraph("DEMANDEUR", heading_style))
    
    demandeur_info = f"""
    <b>Nom:</b> {demande.nom_demandeur}<br/>
    <b>Lien de parenté:</b> {demande.lien_parente}<br/>
    <b>Téléphone:</b> {demande.telephone_demandeur or 'Non renseigné'}<br/>
    """
    
    story.append(Paragraph(demandeur_info, normal_style))
    story.append(Spacer(1, 0.8*cm))
    
    story.append(Paragraph("DÉTAILS DE LA DEMANDE", heading_style))
    
    exhumation_info = f"""
    <b>Motif:</b> {demande.motif}<br/>
    <b>Destination:</b> {demande.get_destination_display()}<br/>
    """
    
    story.append(Paragraph(exhumation_info, normal_style))
    story.append(Spacer(1, 1*cm))
    
    legal_text = """
    <b>AUTORISATION</b><br/><br/>
    Par la présente, l'administration du cimetière autorise l'exhumation du défunt 
    inhumé dans le caveau mentionné ci-dessus, conformément à la demande susmentionnée.<br/><br/>
    Cette autorisation est délivrée sous réserve du respect des réglementations en vigueur 
    relatives aux opérations funéraires.
    """
    
    story.append(Paragraph(legal_text, normal_style))
    story.append(Spacer(1, 2*cm))
    
    signature_data = [
        ['Fait à _________________________', 'Le _________________________'],
        ['', ''],
        ['Signature du demandeur', 'Signature et cachet de l\'administration'],
    ]
    
    signature_table = Table(signature_data, colWidths=[8*cm, 8*cm])
    signature_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 2), (-1, 2), 20),
    ]))
    
    story.append(signature_table)
    
    story.append(Spacer(1, 1*cm))
    footer_text = f"""
    <i>Document généré automatiquement le {now.strftime('%d/%m/%Y à %H:%M')}<br/>
    Gestion du Cimetière - {settings.DEFAULT_FROM_EMAIL}</i>
    """
    story.append(Paragraph(footer_text, ParagraphStyle(
        'Footer',
        parent=normal_style,
        fontSize=8,
        textColor=colors.grey,
        alignment=1
    )))
    
    doc.build(story)
    
    return f'{relative_path}{filename}'


def generer_proces_verbal_exhumation(demande):
    """
    Génère un PDF de procès-verbal d'exhumation.
    
    Args:
        demande: Instance du modèle DemandeExhumation
        
    Returns:
        str: Chemin relatif du fichier PDF généré
    """
    now = datetime.now()
    relative_path = f'exhumations/proces_verbaux/{now.year}/{now.month:02d}/'
    full_path = os.path.join(settings.MEDIA_ROOT, relative_path)
    os.makedirs(full_path, exist_ok=True)
    
    filename = f'proces_verbal_{demande.id}.pdf'
    file_path = os.path.join(full_path, filename)
    
    inhumation = demande.inhumation
    concession = inhumation.concession
    caveau = concession.caveau
    defunt = inhumation.defunt
    
    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=22,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=20,
        alignment=1
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#34495e'),
        spaceAfter=12,
        spaceBefore=12
    )
    
    normal_style = styles['Normal']
    
    story = []
    
    story.append(Paragraph("PROCÈS-VERBAL D'EXHUMATION", title_style))
    story.append(Spacer(1, 0.5*cm))
    
    date_realisation = demande.date_realisation or now
    ref_data = [
        ['Référence:', f'PV-EXH-{demande.id:05d}'],
        ['Date de réalisation:', date_realisation.strftime('%d/%m/%Y')],
    ]
    
    ref_table = Table(ref_data, colWidths=[5*cm, 10*cm])
    ref_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2c3e50')),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    story.append(ref_table)
    story.append(Spacer(1, 0.8*cm))
    
    story.append(Paragraph("DÉFUNT EXHUMÉ", heading_style))
    
    defunt_info = f"""
    <b>Nom:</b> {defunt.nom if defunt else 'Non renseigné'}<br/>
    <b>Prénom:</b> {defunt.prenom if defunt else 'Non renseigné'}<br/>
    <b>Date de décès:</b> {defunt.date_deces.strftime('%d/%m/%Y') if defunt and defunt.date_deces else '-'}<br/>
    """
    
    story.append(Paragraph(defunt_info, normal_style))
    story.append(Spacer(1, 0.8*cm))
    
    story.append(Paragraph("CONCESSION", heading_style))
    
    concession_info = f"""
    <b>Caveau:</b> {caveau.code}<br/>
    <b>Zone:</b> {caveau.zone.nom if caveau.zone else 'Non définie'}<br/>
    <b>N° de contrat:</b> {concession.numero_contrat}<br/>
    """
    
    story.append(Paragraph(concession_info, normal_style))
    story.append(Spacer(1, 0.8*cm))
    
    story.append(Paragraph("OPÉRATION D'EXHUMATION", heading_style))
    
    operation_info = f"""
    <b>Demandeur:</b> {demande.nom_demandeur}<br/>
    <b>Lien de parenté:</b> {demande.lien_parente}<br/>
    <b>Motif:</b> {demande.motif}<br/>
    <b>Destination:</b> {demande.get_destination_display()}<br/>
    """
    
    story.append(Paragraph(operation_info, normal_style))
    story.append(Spacer(1, 1*cm))
    
    constat_text = """
    <b>CONSTAT</b><br/><br/>
    Nous soussignés, représentants de l'administration du cimetière, certifions que 
    l'opération d'exhumation a été réalisée conformément à l'autorisation délivrée 
    sous la référence mentionnée ci-dessus.<br/><br/>
    L'opération s'est déroulée dans le respect des réglementations en vigueur et 
    des normes sanitaires applicables.
    """
    
    story.append(Paragraph(constat_text, normal_style))
    story.append(Spacer(1, 2*cm))
    
    signature_data = [
        ['Fait à _________________________', 'Le _________________________'],
        ['', ''],
        ['Signature du responsable', 'Signature et cachet de l\'administration'],
    ]
    
    signature_table = Table(signature_data, colWidths=[8*cm, 8*cm])
    signature_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 2), (-1, 2), 20),
    ]))
    
    story.append(signature_table)
    
    story.append(Spacer(1, 1*cm))
    footer_text = f"""
    <i>Document généré automatiquement le {now.strftime('%d/%m/%Y à %H:%M')}<br/>
    Gestion du Cimetière - {settings.DEFAULT_FROM_EMAIL}</i>
    """
    story.append(Paragraph(footer_text, ParagraphStyle(
        'Footer',
        parent=normal_style,
        fontSize=8,
        textColor=colors.grey,
        alignment=1
    )))
    
    doc.build(story)
    
    return f'{relative_path}{filename}'