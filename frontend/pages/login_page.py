"""
Page de connexion de l'application.
"""
import flet as ft
from flet import (
    View,
    AppBar,
    Container,
    Column,
    Row,
    Text,
    TextField,
    ElevatedButton,
    TextButton,
    Icon,
    Icons,
    Colors,
    FontWeight,
    TextAlign,
    border_radius,
    alignment,
    padding,
)
from frontend.api_client import api_client, APIError
from frontend.theme import AppColors, AppSpacing, AppComponents, AppTypography


class LoginPage:
    """Page de connexion utilisateur."""
    
    def __init__(self, page: ft.Page, app_state):
        self.page = page
        self.app_state = app_state
        
        # Champs du formulaire
        self.email_field = TextField(
            label="Adresse email",
            prefix_icon=Icons.EMAIL,
            border_radius=border_radius.all(10),
            autofocus=True,
            on_submit=self._on_login,
        )
        
        self.password_field = TextField(
            label="Mot de passe",
            password=True,
            can_reveal_password=True,
            prefix_icon=Icons.LOCK,
            border_radius=border_radius.all(10),
            on_submit=self._on_login,
        )
        
        self.error_text = Text(
            "",
            color=Colors.RED_400,
            size=12,
            text_align=TextAlign.CENTER,
        )
        
        self.login_button = ElevatedButton(
            "Se connecter",
            icon=Icons.LOGIN,
            width=300,
            height=50,
            bgcolor=AppColors.PRIMARY,
            color=Colors.WHITE,
            on_click=self._on_login,
        )
        
        self.loading = ft.ProgressRing(visible=False)
    
    def build(self) -> View:
        """Construit la vue de connexion."""
        
        return View(
            "/login",
            [
                AppBar(
                    title=Text("Gestion Cimetière"),
                    center_title=True,
                    bgcolor=AppColors.PRIMARY,
                    color=Colors.WHITE,
                ),
                Container(
                    content=Column(
                        [
                            # Logo / Icône
                            Icon(
                                Icons.LOCATION_CITY,
                                size=80,
                                color=AppColors.PRIMARY,
                            ),
                            
                            # Titre
                            Text(
                                "Bienvenue",
                                size=32,
                                weight=FontWeight.BOLD,
                                color=AppColors.PRIMARY,
                            ),
                            Text(
                                "Connectez-vous à votre espace",
                                size=16,
                                color=AppColors.TEXT_SECONDARY,
                            ),
                            
                            ft.Divider(height=30),
                            
                            # Formulaire
                            Container(
                                content=Column(
                                    [
                                        self.email_field,
                                        self.password_field,
                                        self.error_text,
                                        self.loading,
                                        self.login_button,
                                        
                                        ft.Divider(height=20),
                                        
                                        # Lien d'inscription
                                        TextButton(
                                            "Pas encore de compte ? S'inscrire",
                                            icon=Icons.PERSON_ADD,
                                            on_click=self._on_register,
                                        ),
                                    ],
                                    spacing=15,
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                width=400,
                                padding=30,
                                border_radius=border_radius.all(15),
                                shadow=ft.BoxShadow(
                                    spread_radius=1,
                                    blur_radius=15,
                                    color=Colors.with_opacity(0.2, Colors.BLACK),
                                    offset=ft.Offset(0, 5),
                                ),
                                bgcolor=Colors.WHITE,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=20,
                    ),
                    alignment=alignment.center,
                    expand=True,
                    padding=20,
                ),
            ],
        )
    
    def _on_login(self, e):
        """Gère la tentative de connexion."""
        email = self.email_field.value
        password = self.password_field.value
        
        # Validation
        if not email or not password:
            self.error_text.value = "Veuillez remplir tous les champs"
            self.page.update()
            return
        
        # Afficher le chargement
        self.error_text.value = ""
        self.login_button.disabled = True
        self.loading.visible = True
        self.page.update()
        
        try:
            # Appel API
            result = api_client.login(email, password)
            
            # Vérifier si MFA requis
            if result.get('requires_mfa'):
                # Stocker les infos temporaires
                self.app_state.temp_user_id = result.get('user_id')
                self.app_state.temp_user_email = email
                self.page.route = "/mfa"
                self.page.update()
            else:
                # Connexion réussie sans MFA
                token = result.get('access_token')
                api_client.set_token(token)
                
                # Récupérer le profil
                profile = api_client.get_profile()
                self.app_state.set_user(profile)
                self.app_state.token = token
                
                self.page.route = "/dashboard"
                self.page.update()
        
        except APIError as e:
            self.error_text.value = f"Erreur : {e.message}"
        except Exception as e:
            self.error_text.value = f"Erreur inattendue : {str(e)}"
        finally:
            # Réinitialiser l'état
            self.login_button.disabled = False
            self.loading.visible = False
            self.page.update()
    
    def _on_register(self, e):
        """Redirige vers la page d'inscription."""
        # Pour l'instant, on affiche un message
        self.page.open(
            ft.AlertDialog(
                title=Text("Inscription"),
                content=Text("L'inscription sera disponible prochainement.\nVeuillez contacter l'administration."),
                actions=[
                    ft.TextButton("OK", on_click=lambda _: self.page.close(self.page.overlay[-1]))
                ],
            )
        )