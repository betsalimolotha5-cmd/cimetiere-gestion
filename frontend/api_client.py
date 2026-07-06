"""
Client API centralisé pour communiquer avec le backend Django.
Gère l'authentification, les requêtes HTTP et les erreurs.
"""
import requests
from typing import Optional, Dict, Any, List
import json
import os
import logging

# Configuration
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000/api')
TIMEOUT = 10

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Exception personnalisée pour les erreurs API."""
    
    def __init__(self, message: str, status_code: int = None, response_data: Dict = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data or {}
        super().__init__(self.message)


class APIClient:
    """Client API pour communiquer avec le backend Django."""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or API_BASE_URL
        self.token: Optional[str] = None
        self.session = requests.Session()
    
    def set_token(self, token: str):
        """Définit le token d'authentification."""
        self.token = token
        if token:
            self.session.headers.update({
                'Authorization': f'Bearer {token}'
            })
        else:
            self.session.headers.pop('Authorization', None)
    
    def clear_token(self):
        """Supprime le token d'authentification."""
        self.token = None
        self.session.headers.pop('Authorization', None)
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Dict = None,
        params: Dict = None,
        files: Dict = None
    ) -> Dict[str, Any]:
        """
        Effectue une requête HTTP.
        
        Args:
            method: Méthode HTTP (GET, POST, PUT, DELETE)
            endpoint: Endpoint API (ex: /accounts/login)
            data: Données à envoyer (pour POST/PUT)
            params: Paramètres de requête (pour GET)
            files: Fichiers à uploader
        
        Returns:
            Dict: Réponse de l'API
        
        Raises:
            APIError: Si la requête échoue
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method == 'GET':
                response = self.session.get(url, params=params, timeout=TIMEOUT)
            elif method == 'POST':
                if files:
                    response = self.session.post(url, data=data, files=files, timeout=TIMEOUT)
                else:
                    response = self.session.post(url, json=data, timeout=TIMEOUT)
            elif method == 'PUT':
                response = self.session.put(url, json=data, timeout=TIMEOUT)
            elif method == 'DELETE':
                response = self.session.delete(url, timeout=TIMEOUT)
            else:
                raise APIError(f"Méthode HTTP non supportée: {method}")
            
            # Vérifier le statut
            if response.status_code >= 400:
                try:
                    error_data = response.json()
                    error_message = error_data.get('detail', error_data.get('message', 'Erreur inconnue'))
                except:
                    error_message = response.text or 'Erreur inconnue'
                
                raise APIError(
                    message=error_message,
                    status_code=response.status_code,
                    response_data=error_data if 'error_data' in locals() else {}
                )
            
            # Retourner la réponse JSON
            return response.json()
        
        except requests.exceptions.Timeout:
            raise APIError("Délai d'attente dépassé. Veuillez réessayer.")
        except requests.exceptions.ConnectionError:
            raise APIError("Impossible de se connecter au serveur. Vérifiez votre connexion.")
        except requests.exceptions.RequestException as e:
            raise APIError(f"Erreur de requête: {str(e)}")
        except json.JSONDecodeError:
            raise APIError("Réponse invalide du serveur")
    
    # === AUTHENTIFICATION ===
    
    def login(self, email: str, password: str) -> Dict[str, Any]:
        """
        Connexion de l'utilisateur.
        
        Returns:
            Dict avec access_token, user_id, requires_mfa, etc.
        """
        return self._make_request(
            'POST',
            '/accounts/login',
            data={'email': email, 'password': password}
        )
    
    def verify_mfa(self, user_id: int, code: str) -> Dict[str, Any]:
        """Vérification du code MFA."""
        return self._make_request(
            'POST',
            '/accounts/mfa/verify',
            data={'user_id': user_id, 'code': code}
        )
    
    def register(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        phone: str,
        national_id: str,
        address: str
    ) -> Dict[str, Any]:
        """Inscription d'un nouveau client."""
        return self._make_request(
            'POST',
            '/accounts/register',
            data={
                'email': email,
                'password': password,
                'first_name': first_name,
                'last_name': last_name,
                'phone': phone,
                'national_id': national_id,
                'address': address,
            }
        )
    
    def get_profile(self) -> Dict[str, Any]:
        """Récupérer le profil de l'utilisateur connecté."""
        return self._make_request('GET', '/accounts/me')
    
    def update_profile(self, **kwargs) -> Dict[str, Any]:
        """Mettre à jour le profil."""
        return self._make_request('PUT', '/accounts/me', data=kwargs)
    
    def change_password(self, old_password: str, new_password: str) -> Dict[str, Any]:
        """Changer le mot de passe."""
        return self._make_request(
            'POST',
            '/accounts/change-password',
            data={'old_password': old_password, 'new_password': new_password}
        )
    
    def logout(self) -> Dict[str, Any]:
        """Déconnexion."""
        return self._make_request('POST', '/accounts/logout')
    
    def resend_mfa(self) -> Dict[str, Any]:
        """Renvoyer le code MFA."""
        return self._make_request('POST', '/accounts/mfa/resend')
    
    # === ZONES ===
    
    def get_zones(self) -> List[Dict[str, Any]]:
        """Récupérer toutes les zones."""
        return self._make_request('GET', '/core/zones')
    
    def get_zone(self, zone_id: int) -> Dict[str, Any]:
        """Récupérer les détails d'une zone."""
        return self._make_request('GET', f'/core/zones/{zone_id}')
    
    def create_zone(self, **kwargs) -> Dict[str, Any]:
        """Créer une nouvelle zone."""
        return self._make_request('POST', '/core/zones', data=kwargs)
    
    # === CAVEAUX ===
    
    def get_caveaux(self, zone_id: int = None, statut: str = None) -> List[Dict[str, Any]]:
        """Récupérer tous les caveaux avec filtres optionnels."""
        params = {}
        if zone_id:
            params['zone_id'] = zone_id
        if statut:
            params['statut'] = statut
        
        return self._make_request('GET', '/core/caveaux', params=params)
    
    def get_caveau(self, caveau_id: int) -> Dict[str, Any]:
        """Récupérer les détails d'un caveau."""
        return self._make_request('GET', f'/core/caveaux/{caveau_id}')
    
    def create_caveau(self, **kwargs) -> Dict[str, Any]:
        """Créer un nouveau caveau."""
        return self._make_request('POST', '/core/caveaux', data=kwargs)
    
    def update_caveau(self, caveau_id: int, **kwargs) -> Dict[str, Any]:
        """Mettre à jour un caveau."""
        return self._make_request('PUT', f'/core/caveaux/{caveau_id}', data=kwargs)
    
    # === RÉSERVATIONS ===
    
    def create_reservation(self, **kwargs) -> Dict[str, Any]:
        """Créer une réservation de caveau."""
        return self._make_request('POST', '/core/reservations', data=kwargs)
    
    def valider_reservation(self, concession_id: int) -> Dict[str, Any]:
        """Valider une réservation (admin)."""
        return self._make_request('POST', f'/core/reservations/{concession_id}/valider')
    
    # === CONCESSIONS ===
    
    def get_concessions(self, statut: str = None, type_concession: str = None) -> List[Dict[str, Any]]:
        """Récupérer toutes les concessions."""
        params = {}
        if statut:
            params['statut'] = statut
        if type_concession:
            params['type_concession'] = type_concession
        
        return self._make_request('GET', '/core/concessions', params=params)
    
    def get_concession(self, concession_id: int) -> Dict[str, Any]:
        """Récupérer les détails d'une concession."""
        return self._make_request('GET', f'/core/concessions/{concession_id}')
    
    # === EXHUMATIONS ===
    
    def get_exhumations(self, statut: str = None) -> List[Dict[str, Any]]:
        """Récupérer toutes les demandes d'exhumation."""
        params = {}
        if statut:
            params['statut'] = statut
        
        return self._make_request('GET', '/core/exhumations', params=params)
    
    def create_exhumation(self, **kwargs) -> Dict[str, Any]:
        """Créer une demande d'exhumation."""
        return self._make_request('POST', '/core/exhumations', data=kwargs)
    
    def valider_exhumation(self, demande_id: int) -> Dict[str, Any]:
        """Valider une demande d'exhumation."""
        return self._make_request('POST', f'/core/exhumations/{demande_id}/valider')
    
    # === STATISTIQUES ===
    
    def get_statistiques(self) -> Dict[str, Any]:
        """Récupérer les statistiques globales."""
        return self._make_request('GET', '/core/statistiques')
    
    # === FACTURES ===
    
    def get_factures(self, statut: str = None, client_id: int = None) -> List[Dict[str, Any]]:
        """Récupérer toutes les factures."""
        params = {}
        if statut:
            params['statut'] = statut
        if client_id:
            params['client_id'] = client_id
        
        return self._make_request('GET', '/billing/factures', params=params)
    
    def get_facture(self, facture_id: int) -> Dict[str, Any]:
        """Récupérer les détails d'une facture."""
        return self._make_request('GET', f'/billing/factures/{facture_id}')
    
    def create_facture(self, **kwargs) -> Dict[str, Any]:
        """Créer une nouvelle facture."""
        return self._make_request('POST', '/billing/factures', data=kwargs)
    
    def update_facture(self, facture_id: int, **kwargs) -> Dict[str, Any]:
        """Mettre à jour une facture."""
        return self._make_request('PUT', f'/billing/factures/{facture_id}', data=kwargs)
    
    def emettre_facture(self, facture_id: int) -> Dict[str, Any]:
        """Émettre une facture."""
        return self._make_request('POST', f'/billing/factures/{facture_id}/emettre')
    
    def annuler_facture(self, facture_id: int, motif: str = '') -> Dict[str, Any]:
        """Annuler une facture."""
        return self._make_request(
            'POST',
            f'/billing/factures/{facture_id}/annuler',
            data={'motif': motif}
        )
    
    # === PAIEMENTS ===
    
    def get_paiements(self, statut: str = None, facture_id: int = None) -> List[Dict[str, Any]]:
        """Récupérer tous les paiements."""
        params = {}
        if statut:
            params['statut'] = statut
        if facture_id:
            params['facture_id'] = facture_id
        
        return self._make_request('GET', '/billing/paiements', params=params)
    
    def enregistrer_paiement(self, **kwargs) -> Dict[str, Any]:
        """Enregistrer un paiement."""
        return self._make_request('POST', '/billing/paiements', data=kwargs)
    
    def valider_paiement(self, paiement_id: int) -> Dict[str, Any]:
        """Valider un paiement."""
        return self._make_request('POST', f'/billing/paiements/{paiement_id}/valider')
    
    # === STATISTIQUES FINANCIÈRES ===
    
    def get_statistiques_financieres(self) -> Dict[str, Any]:
        """Récupérer les statistiques financières."""
        return self._make_request('GET', '/billing/statistiques')
    
    # === NOTIFICATIONS ===
    
    def get_notifications(self, limit: int = 10, non_lues_only: bool = False) -> Dict[str, Any]:
        """Récupérer les notifications."""
        params = {'limit': limit}
        if non_lues_only:
            params['non_lues_only'] = 'true'
        
        return self._make_request('GET', '/notifications/api/liste/', params=params)
    
    def compter_notifications_non_lues(self) -> int:
        """Compter les notifications non lues."""
        result = self._make_request('GET', '/notifications/api/compter-non-lues/')
        return result.get('count', 0)


# Instance globale du client API
api_client = APIClient()