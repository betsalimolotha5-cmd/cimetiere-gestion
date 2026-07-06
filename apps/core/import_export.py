"""
Service d'import/export de données CSV.
"""
import io
import csv
from datetime import datetime
from django.db import transaction
from django.core.exceptions import ValidationError
from apps.core.models import Zone, Caveau, Concession, Defunt


class ImportCSVService:
    """Service d'import CSV."""
    
    @staticmethod
    def importer_zones(fichier_csv):
        """
        Importe des zones depuis un fichier CSV.
        
        Format attendu:
        code,nom,type_zone,est_exploitable,superficie
        Z01,Zone Nord,SECTION,True,500.00
        """
        resultats = {'success': 0, 'errors': 0, 'messages': []}
        
        try:
            content = fichier_csv.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(content))
            
            with transaction.atomic():
                for row_num, row in enumerate(reader, start=2):
                    try:
                        # Validation
                        if not row.get('code'):
                            raise ValidationError(f"Ligne {row_num}: code requis")
                        
                        if Zone.objects.filter(code=row['code']).exists():
                            raise ValidationError(f"Ligne {row_num}: code {row['code']} existe déjà")
                        
                        # Création
                        Zone.objects.create(
                            code=row['code'],
                            nom=row.get('nom', ''),
                            type_zone=row.get('type_zone', Zone.TypeZone.SECTION),
                            est_exploitable=row.get('est_exploitable', 'True').lower() == 'true',
                            superficie=float(row.get('superficie', 0))
                        )
                        resultats['success'] += 1
                        resultats['messages'].append(f"Ligne {row_num}: Zone {row['code']} importée")
                    
                    except Exception as e:
                        resultats['errors'] += 1
                        resultats['messages'].append(f"Ligne {row_num}: Erreur - {str(e)}")
        
        except Exception as e:
            resultats['messages'].append(f"Erreur globale: {str(e)}")
        
        return resultats
    
    @staticmethod
    def importer_caveaux(fichier_csv):
        """
        Importe des caveaux depuis un fichier CSV.
        
        Format attendu:
        code,numero,zone_code,type_caveau,longueur,largeur,profondeur,prix_concession
        C001,1A,Z01,INDIVIDUEL,2.5,1.2,1.5,5000.00
        """
        resultats = {'success': 0, 'errors': 0, 'messages': []}
        
        try:
            content = fichier_csv.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(content))
            
            with transaction.atomic():
                for row_num, row in enumerate(reader, start=2):
                    try:
                        if not row.get('code'):
                            raise ValidationError(f"Ligne {row_num}: code requis")
                        
                        if Caveau.objects.filter(code=row['code']).exists():
                            raise ValidationError(f"Ligne {row_num}: code {row['code']} existe déjà")
                        
                        # Trouver la zone
                        zone_code = row.get('zone_code')
                        try:
                            zone = Zone.objects.get(code=zone_code)
                        except Zone.DoesNotExist:
                            raise ValidationError(f"Ligne {row_num}: zone {zone_code} introuvable")
                        
                        Caveau.objects.create(
                            code=row['code'],
                            numero=row.get('numero', ''),
                            zone=zone,
                            type_caveau=row.get('type_caveau', Caveau.TypeCaveau.INDIVIDUEL),
                            longueur=float(row.get('longueur', 2.5)),
                            largeur=float(row.get('largeur', 1.2)),
                            profondeur=float(row.get('profondeur', 1.5)),
                            prix_concession=float(row.get('prix_concession', 0)),
                            statut=Caveau.Statut.DISPONIBLE
                        )
                        resultats['success'] += 1
                        resultats['messages'].append(f"Ligne {row_num}: Caveau {row['code']} importé")
                    
                    except Exception as e:
                        resultats['errors'] += 1
                        resultats['messages'].append(f"Ligne {row_num}: Erreur - {str(e)}")
        
        except Exception as e:
            resultats['messages'].append(f"Erreur globale: {str(e)}")
        
        return resultats
    
    @staticmethod
    def importer_defunts(fichier_csv):
        """
        Importe des défunts depuis un fichier CSV.
        
        Format attendu:
        nom,prenom,date_naissance,date_deces,sexe,numero_identite
        DUPONT,Jean,1940-05-15,2024-01-10,M,123456789
        """
        resultats = {'success': 0, 'errors': 0, 'messages': []}
        
        try:
            content = fichier_csv.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(content))
            
            with transaction.atomic():
                for row_num, row in enumerate(reader, start=2):
                    try:
                        if not row.get('nom') or not row.get('prenom'):
                            raise ValidationError(f"Ligne {row_num}: nom et prénom requis")
                        
                        Defunt.objects.create(
                            nom=row['nom'].upper(),
                            prenom=row['prenom'].title(),
                            date_naissance=datetime.strptime(row['date_naissance'], '%Y-%m-%d').date() if row.get('date_naissance') else None,
                            date_deces=datetime.strptime(row['date_deces'], '%Y-%m-%d').date() if row.get('date_deces') else None,
                            sexe=row.get('sexe', 'M'),
                            numero_identite=row.get('numero_identite', '')
                        )
                        resultats['success'] += 1
                        resultats['messages'].append(f"Ligne {row_num}: Défunt {row['nom']} {row['prenom']} importé")
                    
                    except Exception as e:
                        resultats['errors'] += 1
                        resultats['messages'].append(f"Ligne {row_num}: Erreur - {str(e)}")
        
        except Exception as e:
            resultats['messages'].append(f"Erreur globale: {str(e)}")
        
        return resultats


class ExportCSVService:
    """Service d'export CSV."""
    
    @staticmethod
    def exporter_zones():
        """Exporte toutes les zones en CSV."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['code', 'nom', 'type_zone', 'est_exploitable', 'superficie'])
        
        for zone in Zone.objects.all():
            writer.writerow([
                zone.code,
                zone.nom,
                zone.type_zone,
                zone.est_exploitable,
                zone.superficie
            ])
        
        buffer = io.BytesIO()
        buffer.write(output.getvalue().encode('utf-8'))
        buffer.seek(0)
        return buffer
    
    @staticmethod
    def exporter_caveaux():
        """Exporte tous les caveaux en CSV."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['code', 'numero', 'zone_code', 'zone_nom', 'type_caveau', 
                        'longueur', 'largeur', 'profondeur', 'statut', 'prix_concession'])
        
        for caveau in Caveau.objects.select_related('zone').all():
            writer.writerow([
                caveau.code,
                caveau.numero,
                caveau.zone.code,
                caveau.zone.nom,
                caveau.type_caveau,
                caveau.longueur,
                caveau.largeur,
                caveau.profondeur,
                caveau.statut,
                caveau.prix_concession
            ])
        
        buffer = io.BytesIO()
        buffer.write(output.getvalue().encode('utf-8'))
        buffer.seek(0)
        return buffer
    
    @staticmethod
    def exporter_concessions():
        """Exporte toutes les concessions en CSV."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['numero_contrat', 'concessionnaire_email', 'caveau_code', 
                        'type_concession', 'duree_annees', 'date_debut', 'date_fin', 
                        'statut', 'montant_total'])
        
        for concession in Concession.objects.select_related('concessionnaire', 'caveau').all():
            writer.writerow([
                concession.numero_contrat,
                concession.concessionnaire.email if concession.concessionnaire else '',
                concession.caveau.code if concession.caveau else '',
                concession.type_concession,
                concession.duree_annees,
                concession.date_debut.strftime('%Y-%m-%d') if concession.date_debut else '',
                concession.date_fin.strftime('%Y-%m-%d') if concession.date_fin else '',
                concession.statut,
                concession.montant_total
            ])
        
        buffer = io.BytesIO()
        buffer.write(output.getvalue().encode('utf-8'))
        buffer.seek(0)
        return buffer
    
    @staticmethod
    def exporter_defunts():
        """Exporte tous les défunts en CSV."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['nom', 'prenom', 'date_naissance', 'date_deces', 'sexe', 'numero_identite'])
        
        for defunt in Defunt.objects.all():
            writer.writerow([
                defunt.nom,
                defunt.prenom,
                defunt.date_naissance.strftime('%Y-%m-%d') if defunt.date_naissance else '',
                defunt.date_deces.strftime('%Y-%m-%d') if defunt.date_deces else '',
                defunt.sexe,
                defunt.numero_identite
            ])
        
        buffer = io.BytesIO()
        buffer.write(output.getvalue().encode('utf-8'))
        buffer.seek(0)
        return buffer