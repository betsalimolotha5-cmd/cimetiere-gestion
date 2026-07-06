"""
Vues pour la gestion des paiements.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from decimal import Decimal
from .models import Facture, Paiement, TransactionFinanciere


@login_required
def mes_factures(request):
    """Liste des factures du client connecté."""
    factures = Facture.objects.filter(
        client=request.user
    ).select_related('concession', 'concession__caveau', 'concession__caveau__zone')
    
    context = {
        'factures': factures,
    }
    return render(request, 'billing/mes_factures.html', context)


@login_required
def facture_detail(request, facture_id):
    """Détail d'une facture avec option de paiement."""
    facture = get_object_or_404(
        Facture,
        id=facture_id,
        client=request.user
    )
    
    paiements = facture.paiements.all().order_by('-date_paiement')
    
    context = {
        'facture': facture,
        'paiements': paiements,
    }
    return render(request, 'billing/facture_detail.html', context)


@login_required
def paiement_form(request, facture_id):
    """Formulaire de paiement pour une facture."""
    facture = get_object_or_404(
        Facture,
        id=facture_id,
        client=request.user
    )
    
    if facture.statut == Facture.StatutFacture.ANNULEE:
        messages.error(request, 'Cette facture est annulée.')
        return redirect('facture_detail', facture_id=facture.id)
    
    if facture.est_payee():
        messages.info(request, 'Cette facture est déjà entièrement payée.')
        return redirect('facture_detail', facture_id=facture.id)
    
    if request.method == 'POST':
        montant = Decimal(request.POST.get('montant', '0'))
        mode_paiement = request.POST.get('mode_paiement', '')
        reference = request.POST.get('reference_transaction', '').strip()
        telephone = request.POST.get('numero_telephone', '').strip()
        
        # Validation
        erreurs = []
        if montant <= 0:
            erreurs.append('Le montant doit être supérieur à 0.')
        if montant > facture.montant_restant:
            erreurs.append(f'Le montant ne peut pas dépasser {facture.montant_restant} FCFA.')
        if not mode_paiement:
            erreurs.append('Veuillez sélectionner un mode de paiement.')
        
        # Validation spécifique pour Mobile Money
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
            
            # Créer la transaction financière
            TransactionFinanciere.objects.create(
                type_transaction=TransactionFinanciere.TypeTransaction.PAIEMENT_RECUE,
                montant=montant,
                sens='ENTREE',
                facture=facture,
                paiement=paiement,
                client=request.user,
                description=f'Paiement reçu pour facture {facture.numero_facture}',
                enregistre_par=request.user
            )
            
            messages.success(
                request,
                f'Votre paiement de {montant:,.2f} FCFA a été enregistré. '
                f'Il est en attente de validation par l\'administration.'
            )
            return redirect('facture_detail', facture_id=facture.id)
    
    context = {
        'facture': facture,
    }
    return render(request, 'billing/paiement_form.html', context)