"""
Services métier pour la facturation et la gestion des paiements.
"""
from django.db import transaction
from django.utils import timezone
from django.core.mail import EmailMessage
from django.conf import settings
from django.template.loader import render_to_string
from decimal import Decimal
from typing import Optional, List, Dict, Any
from datetime import date, timedelta
import logging
import uuid

from .models import Facture, Paiement, TransactionFinanciere
from apps.core.models import Concession
from apps.accounts.models import User

logger = logging.getLogger('audit')


class FactureService:
    """Service de gestion des factures."""
    
    @staticmethod
    @transaction.atomic
    def creer_facture(
        concession: Concession,
        client: User,
        montant_ht: Decimal,
        taux_tva: Decimal = Decimal('0.00'),
        date_emission: Optional[date] = None,
        date_echeance: Optional[date] = None,
        description: str = '',
        notes: str = '',
        cree_par: Optional[User] = None
    ) -> Facture:
        """Crée une nouvelle facture pour une concession."""
        if not date_emission:
            date_emission = timezone.now().date()
        
        if not date_echeance:
            date_echeance = date_emission + timedelta(days=30)
        
        # Générer un numéro de facture unique
        numero_facture = FactureService.generer_numero_facture()
        
        facture = Facture.objects.create(
            numero_facture=numero_facture,
            concession=concession,
            client=client,
            montant_ht=montant_ht,
            taux_tva=taux_tva,
            date_emission=date_emission,
            date_echeance=date_echeance,
            description=description or f"Concession {concession.numero_contrat} - Caveau {concession.caveau.code}",
            notes=notes,
            statut=Facture.StatutFacture.BROUILLON,
            cree_par=cree_par,
        )
        
        # Créer une transaction financière
        TransactionFinanciere.objects.create(
            type_transaction=TransactionFinanciere.TypeTransaction.FACTURE_EMISE,
            montant=facture.montant_total,
            sens='ENTREE',
            facture=facture,
            client=client,
            description=f"Facture {numero_facture} créée pour concession {concession.numero_contrat}",
            enregistre_par=cree_par,
        )
        
        logger.info(
            f"INVOICE_CREATED: numero={numero_facture}, "
            f"montant={facture.montant_total}, by={cree_par.email if cree_par else 'system'}"
        )
        
        return facture
    
    @staticmethod
    def generer_numero_facture() -> str:
        """Génère un numéro de facture unique."""
        date_str = timezone.now().strftime('%Y%m%d')
        count_today = Facture.objects.filter(
            date_emission=timezone.now().date()
        ).count()
        return f"FACT-{date_str}-{count_today + 1:04d}"
    
    @staticmethod
    @transaction.atomic
    def emettre_facture(facture: Facture, user: User) -> Facture:
        """Émet une facture (passe de BROUILLON à EMISE)."""
        if facture.statut != Facture.StatutFacture.BROUILLON:
            raise ValueError("Seules les factures en brouillon peuvent être émises.")
        
        facture.statut = Facture.StatutFacture.EMISE
        facture.save()
        
        logger.info(f"INVOICE_ISSUED: numero={facture.numero_facture}, by={user.email}")
        
        return facture
    
    @staticmethod
    @transaction.atomic
    def annuler_facture(facture: Facture, motif: str, user: User) -> Facture:
        """Annule une facture."""
        if facture.statut == Facture.StatutFacture.PAYEE:
            raise ValueError("Impossible d'annuler une facture payée.")
        
        facture.annuler(motif, user)
        
        # Créer une transaction d'annulation
        TransactionFinanciere.objects.create(
            type_transaction=TransactionFinanciere.TypeTransaction.ANNULATION,
            montant=facture.montant_total,
            sens='SORTIE',
            facture=facture,
            client=facture.client,
            description=f"Annulation facture {facture.numero_facture}: {motif}",
            enregistre_par=user,
        )
        
        return facture
    
    @staticmethod
    def get_factures_en_retard() -> List[Facture]:
        """Récupère toutes les factures en retard de paiement."""
        return list(
            Facture.objects.filter(
                statut__in=[
                    Facture.StatutFacture.EMISE,
                    Facture.StatutFacture.PARTIELLEMENT_PAYEE
                ],
                date_echeance__lt=timezone.now().date()
            ).select_related('client', 'concession').order_by('date_echeance')
        )
    
    @staticmethod
    def get_factures_client(client: User) -> List[Facture]:
        """Récupère toutes les factures d'un client."""
        return list(
            Facture.objects.filter(client=client)
            .select_related('concession')
            .order_by('-date_emission')
        )


class PaiementService:
    """Service de gestion des paiements."""
    
    @staticmethod
    @transaction.atomic
    def enregistrer_paiement(
        facture: Facture,
        montant: Decimal,
        mode_paiement: str,
        reference_transaction: str = '',
        numero_telephone: str = '',
        notes: str = '',
        client: Optional[User] = None,
        auto_valider: bool = False,
        valide_par: Optional[User] = None
    ) -> Paiement:
        """Enregistre un paiement pour une facture."""
        if facture.statut == Facture.StatutFacture.ANNULEE:
            raise ValueError("Impossible de payer une facture annulée.")
        
        if montant > facture.montant_restant:
            raise ValueError(f"Le montant dépasse le restant dû ({facture.montant_restant} FC).")
        
        if not client:
            client = facture.client
        
        # Générer un numéro de transaction
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        numero_transaction = f"PAY-{timestamp}-{uuid.uuid4().hex[:6].upper()}"
        
        paiement = Paiement.objects.create(
            numero_transaction=numero_transaction,
            facture=facture,
            client=client,
            montant=montant,
            mode_paiement=mode_paiement,
            reference_transaction=reference_transaction,
            numero_telephone=numero_telephone,
            statut=Paiement.StatutPaiement.VALIDE if auto_valider else Paiement.StatutPaiement.EN_ATTENTE,
            notes=notes,
        )
        
        # Si auto-validation, mettre à jour la facture immédiatement
        if auto_valider and valide_par:
            paiement.valider(valide_par)
            facture.montant_paye += montant
            facture.save()
            
            # Créer une transaction financière
            TransactionFinanciere.objects.create(
                type_transaction=TransactionFinanciere.TypeTransaction.PAIEMENT_RECUE,
                montant=montant,
                sens='ENTREE',
                facture=facture,
                paiement=paiement,
                client=client,
                description=f"Paiement reçu pour facture {facture.numero_facture}",
                enregistre_par=valide_par,
            )
        
        logger.info(
            f"PAYMENT_RECORDED: transaction={numero_transaction}, "
            f"montant={montant}, mode={mode_paiement}"
        )
        
        return paiement
    
    @staticmethod
    @transaction.atomic
    def valider_paiement(paiement: Paiement, validateur: User) -> Paiement:
        """Valide un paiement en attente."""
        if paiement.statut != Paiement.StatutPaiement.EN_ATTENTE:
            raise ValueError("Seuls les paiements en attente peuvent être validés.")
        
        paiement.valider(validateur)
        
        # Mettre à jour la facture
        facture = paiement.facture
        facture.montant_paye += paiement.montant
        facture.save()
        
        # Créer une transaction financière
        TransactionFinanciere.objects.create(
            type_transaction=TransactionFinanciere.TypeTransaction.PAIEMENT_RECUE,
            montant=paiement.montant,
            sens='ENTREE',
            facture=facture,
            paiement=paiement,
            client=paiement.client,
            description=f"Paiement validé pour facture {facture.numero_facture}",
            enregistre_par=validateur,
        )
        
        return paiement
    
    @staticmethod
    @transaction.atomic
    def refuser_paiement(paiement: Paiement, motif: str, validateur: User) -> Paiement:
        """Refuse un paiement."""
        paiement.refuser(motif, validateur)
        return paiement
    
    @staticmethod
    @transaction.atomic
    def rembourser_paiement(paiement: Paiement, motif: str, user: User) -> Paiement:
        """Rembourse un paiement."""
        if paiement.statut != Paiement.StatutPaiement.VALIDE:
            raise ValueError("Seuls les paiements validés peuvent être remboursés.")
        
        paiement.rembourser(motif, user)
        
        # Mettre à jour la facture
        facture = paiement.facture
        facture.montant_paye -= paiement.montant
        facture.save()
        
        # Créer une transaction de remboursement
        TransactionFinanciere.objects.create(
            type_transaction=TransactionFinanciere.TypeTransaction.REMBOURSEMENT,
            montant=paiement.montant,
            sens='SORTIE',
            facture=facture,
            paiement=paiement,
            client=paiement.client,
            description=f"Remboursement pour facture {facture.numero_facture}: {motif}",
            enregistre_par=user,
        )
        
        return paiement


class PDFService:
    """Service de génération de documents PDF."""
    
    @staticmethod
    def generer_facture_pdf(facture: Facture) -> bytes:
        """Génère le PDF d'une facture."""
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from io import BytesIO
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#2C3E50'),
            spaceAfter=30,
            alignment=1  # Center
        )
        
        elements = []
        
        # Titre
        elements.append(Paragraph("FACTURE", title_style))
        elements.append(Spacer(1, 0.5*cm))
        
        # Informations facture
        facture_data = [
            ['N° Facture:', facture.numero_facture],
            ['Date d\'émission:', facture.date_emission.strftime('%d/%m/%Y')],
            ['Date d\'échéance:', facture.date_echeance.strftime('%d/%m/%Y')],
            ['Statut:', facture.get_statut_display()],
        ]
        
        facture_table = Table(facture_data, colWidths=[5*cm, 10*cm])
        facture_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(facture_table)
        elements.append(Spacer(1, 0.5*cm))
        
        # Informations client
        elements.append(Paragraph("<b>Client:</b>", styles['Heading2']))
        client_data = [
            ['Nom:', facture.client.get_full_name()],
            ['Email:', facture.client.email],
            ['Téléphone:', facture.client.phone or 'N/A'],
            ['Adresse:', facture.client.address or 'N/A'],
        ]
        
        client_table = Table(client_data, colWidths=[5*cm, 10*cm])
        client_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(client_table)
        elements.append(Spacer(1, 0.5*cm))
        
        # Description
        elements.append(Paragraph("<b>Description:</b>", styles['Heading2']))
        elements.append(Paragraph(facture.description, styles['Normal']))
        elements.append(Spacer(1, 0.5*cm))
        
        # Montants
        elements.append(Paragraph("<b>Détails financiers:</b>", styles['Heading2']))
        montant_data = [
            ['Montant HT:', f"{facture.montant_ht:,.2f} FC"],
            ['TVA:', f"{facture.taux_tva}%"],
            ['Montant TVA:', f"{facture.montant_tva:,.2f} FC"],
            ['', ''],
            ['MONTANT TOTAL TTC:', f"{facture.montant_total:,.2f} FC"],
            ['Montant payé:', f"{facture.montant_paye:,.2f} FC"],
            ['Montant restant:', f"{facture.montant_restant:,.2f} FC"],
        ]
        
        montant_table = Table(montant_data, colWidths=[8*cm, 7*cm])
        montant_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LINEABOVE', (0, 3), (-1, 3), 1, colors.black),
            ('FONTNAME', (0, 4), (-1, 4), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 4), (-1, 4), 12),
            ('TEXTCOLOR', (0, 4), (-1, 4), colors.HexColor('#27AE60')),
        ]))
        elements.append(montant_table)
        
        # Pied de page
        elements.append(Spacer(1, 1*cm))
        elements.append(Paragraph(
            "<i>Merci de régler cette facture avant la date d'échéance indiquée.</i>",
            styles['Italic']
        ))
        
        doc.build(elements)
        pdf = buffer.getvalue()
        buffer.close()
        
        return pdf
    
    @staticmethod
    def sauvegarder_facture_pdf(facture: Facture) -> str:
        """Génère et sauvegarde le PDF d'une facture."""
        pdf_content = PDFService.generer_facture_pdf(facture)
        
        # Créer le nom de fichier
        filename = f"factures/pdf/{timezone.now().year}/{timezone.now().month:02d}/{facture.numero_facture}.pdf"
        
        # Sauvegarder le fichier
        from django.core.files.base import ContentFile
        facture.fichier_pdf.save(filename, ContentFile(pdf_content))
        
        logger.info(f"PDF_GENERATED: facture={facture.numero_facture}")
        
        return facture.fichier_pdf.url


class EmailService:
    """Service d'envoi d'emails pour les factures."""
    
    @staticmethod
    def envoyer_facture_email(facture: Facture) -> bool:
        """Envoie la facture par email au client."""
        try:
            # Générer le PDF si pas encore fait
            if not facture.fichier_pdf:
                PDFService.sauvegarder_facture_pdf(facture)
            
            # Préparer l'email
            subject = f"Votre facture {facture.numero_facture} - Cimetière"
            
            html_message = render_to_string('emails/invoice.html', {
                'facture': facture,
                'client': facture.client,
            })
            
            email = EmailMessage(
                subject=subject,
                body=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[facture.client.email],
            )
            email.content_subtype = 'html'
            
            # Joindre le PDF
            if facture.fichier_pdf:
                email.attach_file(facture.fichier_pdf.path)
            
            email.send(fail_silently=False)
            
            # Mettre à jour le statut
            facture.email_envoye = True
            facture.date_envoi_email = timezone.now()
            facture.save(update_fields=['email_envoye', 'date_envoi_email'])
            
            logger.info(f"INVOICE_EMAIL_SENT: facture={facture.numero_facture}, to={facture.client.email}")
            
            return True
        
        except Exception as e:
            logger.error(f"INVOICE_EMAIL_FAILED: facture={facture.numero_facture}, error={str(e)}")
            return False
    
    @staticmethod
    def envoyer_rappel_paiement(facture: Facture) -> bool:
        """Envoie un rappel de paiement pour une facture en retard."""
        try:
            subject = f"Rappel: Facture {facture.numero_facture} en retard de paiement"
            
            html_message = render_to_string('emails/payment_reminder.html', {
                'facture': facture,
                'client': facture.client,
                'jours_retard': facture.jours_retard(),
            })
            
            email = EmailMessage(
                subject=subject,
                body=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[facture.client.email],
            )
            email.content_subtype = 'html'
            
            email.send(fail_silently=False)
            
            logger.info(f"PAYMENT_REMINDER_SENT: facture={facture.numero_facture}, to={facture.client.email}")
            
            return True
        
        except Exception as e:
            logger.error(f"PAYMENT_REMINDER_FAILED: facture={facture.numero_facture}, error={str(e)}")
            return False


class StatistiquesFinancieresService:
    """Service de calcul des statistiques financières."""
    
    @staticmethod
    def get_statistiques_globales() -> Dict[str, Any]:
        """Calcule les statistiques financières globales."""
        from django.db.models import Sum, Count
        
        # Statistiques des factures
        total_factures = Facture.objects.count()
        factures_payees = Facture.objects.filter(statut=Facture.StatutFacture.PAYEE).count()
        factures_en_retard = Facture.objects.filter(
            statut__in=[Facture.StatutFacture.EMISE, Facture.StatutFacture.PARTIELLEMENT_PAYEE],
            date_echeance__lt=timezone.now().date()
        ).count()
        factures_en_attente = Facture.objects.filter(
            statut__in=[Facture.StatutFacture.EMISE, Facture.StatutFacture.PARTIELLEMENT_PAYEE]
        ).count()
        
        # Revenus
        revenus_mois = Paiement.objects.filter(
            statut=Paiement.StatutPaiement.VALIDE,
            date_paiement__month=timezone.now().month,
            date_paiement__year=timezone.now().year
        ).aggregate(total=Sum('montant'))['total'] or Decimal('0.00')
        
        revenus_annee = Paiement.objects.filter(
            statut=Paiement.StatutPaiement.VALIDE,
            date_paiement__year=timezone.now().year
        ).aggregate(total=Sum('montant'))['total'] or Decimal('0.00')
        
        # Totaux
        total_recu = Paiement.objects.filter(
            statut=Paiement.StatutPaiement.VALIDE
        ).aggregate(total=Sum('montant'))['total'] or Decimal('0.00')
        
        total_restant = Facture.objects.filter(
            statut__in=[Facture.StatutFacture.EMISE, Facture.StatutFacture.PARTIELLEMENT_PAYEE]
        ).aggregate(total=Sum('montant_restant'))['total'] or Decimal('0.00')
        
        # Paiements par mode
        paiements_par_mode = {}
        for mode in Paiement.ModePaiement.choices:
            montant = Paiement.objects.filter(
                statut=Paiement.StatutPaiement.VALIDE,
                mode_paiement=mode[0]
            ).aggregate(total=Sum('montant'))['total'] or Decimal('0.00')
            paiements_par_mode[mode[1]] = str(montant)
        
        return {
            'total_factures': total_factures,
            'factures_payees': factures_payees,
            'factures_en_retard': factures_en_retard,
            'factures_en_attente': factures_en_attente,
            'revenus_mois': revenus_mois,
            'revenus_annee': revenus_annee,
            'total_recu': total_recu,
            'total_restant': total_restant,
            'paiements_par_mode': paiements_par_mode,
        }
    
    @staticmethod
    def get_statistiques_client(client: User) -> Dict[str, Any]:
        """Calcule les statistiques financières d'un client."""
        from django.db.models import Sum
        
        factures_client = Facture.objects.filter(client=client)
        
        total_facture = factures_client.count()
        total_paye = factures_client.aggregate(total=Sum('montant_paye'))['total'] or Decimal('0.00')
        total_du = factures_client.aggregate(total=Sum('montant_restant'))['total'] or Decimal('0.00')
        
        factures_payees = factures_client.filter(statut=Facture.StatutFacture.PAYEE).count()
        factures_en_retard = factures_client.filter(
            statut__in=[Facture.StatutFacture.EMISE, Facture.StatutFacture.PARTIELLEMENT_PAYEE],
            date_echeance__lt=timezone.now().date()
        ).count()
        
        return {
            'total_factures': total_facture,
            'factures_payees': factures_payees,
            'factures_en_retard': factures_en_retard,
            'total_paye': total_paye,
            'total_du': total_du,
        }