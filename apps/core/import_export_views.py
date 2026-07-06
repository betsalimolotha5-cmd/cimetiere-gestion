"""
Vues API pour l'import/export CSV.
"""
from django.http import HttpResponse
from django.utils import timezone
from ninja import Router, File, UploadedFile
from apps.core.import_export import ImportCSVService, ExportCSVService
from apps.accounts.services import PermissionService

router = Router(tags=["Import/Export"])


# === IMPORT ===

@router.post("/import/zones")
def importer_zones(request, file: UploadedFile = File(...)):
    """Importe des zones depuis un CSV."""
    if not PermissionService.can_manage_caveaux(request.user):
        return {"success": False, "message": "Accès refusé"}
    
    resultats = ImportCSVService.importer_zones(file)
    return {
        "success": resultats['errors'] == 0,
        "imported": resultats['success'],
        "errors": resultats['errors'],
        "messages": resultats['messages'][:10]  # Limite les messages
    }


@router.post("/import/caveaux")
def importer_caveaux(request, file: UploadedFile = File(...)):
    """Importe des caveaux depuis un CSV."""
    if not PermissionService.can_manage_caveaux(request.user):
        return {"success": False, "message": "Accès refusé"}
    
    resultats = ImportCSVService.importer_caveaux(file)
    return {
        "success": resultats['errors'] == 0,
        "imported": resultats['success'],
        "errors": resultats['errors'],
        "messages": resultats['messages'][:10]
    }


@router.post("/import/defunts")
def importer_defunts(request, file: UploadedFile = File(...)):
    """Importe des défunts depuis un CSV."""
    if not PermissionService.can_manage_caveaux(request.user):
        return {"success": False, "message": "Accès refusé"}
    
    resultats = ImportCSVService.importer_defunts(file)
    return {
        "success": resultats['errors'] == 0,
        "imported": resultats['success'],
        "errors": resultats['errors'],
        "messages": resultats['messages'][:10]
    }


# === EXPORT ===

@router.get("/export/zones")
def exporter_zones(request):
    """Exporte les zones en CSV."""
    if not PermissionService.can_manage_caveaux(request.user):
        return {"success": False, "message": "Accès refusé"}
    
    buffer = ExportCSVService.exporter_zones()
    response = HttpResponse(buffer.getvalue(), content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="zones_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    return response


@router.get("/export/caveaux")
def exporter_caveaux(request):
    """Exporte les caveaux en CSV."""
    if not PermissionService.can_manage_caveaux(request.user):
        return {"success": False, "message": "Accès refusé"}
    
    buffer = ExportCSVService.exporter_caveaux()
    response = HttpResponse(buffer.getvalue(), content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="caveaux_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    return response


@router.get("/export/concessions")
def exporter_concessions(request):
    """Exporte les concessions en CSV."""
    if not PermissionService.can_view_financial_stats(request.user):
        return {"success": False, "message": "Accès refusé"}
    
    buffer = ExportCSVService.exporter_concessions()
    response = HttpResponse(buffer.getvalue(), content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="concessions_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    return response


@router.get("/export/defunts")
def exporter_defunts(request):
    """Exporte les défunts en CSV."""
    if not PermissionService.can_manage_caveaux(request.user):
        return {"success": False, "message": "Accès refusé"}
    
    buffer = ExportCSVService.exporter_defunts()
    response = HttpResponse(buffer.getvalue(), content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="defunts_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    return response