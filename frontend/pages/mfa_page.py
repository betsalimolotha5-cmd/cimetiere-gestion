"""
Page de vérification MFA (Multi-Factor Authentication).
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
from frontend.theme import AppColors, AppSpacing


class MFAPage:
    """Page de vérification du code MFA."""
    
    def __init__(self, page: ft.Page, app_state):
        self.page = page
        self.app_state = app_state
        
        # Champ pour le code MFA
        self.code_field = TextField(
            label="Code de vérification",
            prefix_icon=Icons.SECURITY,
            border_radius=border_radius.all(10),
            autofocus=True,
            max_length=6,
            text_align=TextAlign.CENTER,
            text_size=24,
            on_submit=self._on_verify,
        )
        
        self.error_text = Text(
            "",
            color=Colors.RED_400,
            size=12,
            text_align=TextAlign.CENTER,
        )
        
        self.verify_button = ElevatedButton(
            "Vérifier le code",
            icon=Icons.CHECK_CIRCLE,
            width=300,
            height=50,
            bgcolor=AppColors.PRIMARY,
            color=Colors.WHITE,
            on_click=self._on_verify,
        )
        
        self.resend_button = TextButton(
            "Renvoyer le code",
            icon=Icons.REFRESH,
            on_click=self._on_resend,
        )
        
        self.loading = ft.ProgressRing(visible=False)
        
        # Info utilisateur
        self.user_email = getattr(app_state, 'temp_user_email', '')
    
    def build(self) -> View:
        """Construit la vue de vérification MFA."""
        
        return View(
            "/mfa",
            [
                AppBar(
                    title=Text("Vérification MFA"),
                    center_title=True,
                    bgcolor=AppColors.PRIMARY,
                    color=Colors.WHITE,
                ),
                Container(
                    content=Column(
                        [
                            # Icône de sécurité
                            Icon(
                                Icons.SECURITY,
                                size=80,
                                color=AppColors.PRIMARY,
                            ),
                            
                            # Titre
                            Text(
                                "Authentification à double facteur",
                                size=24,
                                weight=FontWeight.BOLD,
                                color=AppColors.TEXT_PRIMARY,
                                text_align=TextAlign.CENTER,
                            ),
                            
                            Text(
                                f"Un code à 6 chiffres a été envoyé à :\n{self.user_email}",
                                size=14,
                                color=AppColors.TEXT_SECONDARY,
                                text_align=TextAlign.CENTER,
                            ),
                            
                            ft.Divider(height=30),
                            
                            # Formulaire
                            Container(
                                content=Column(
                                    [
                                        self.code_field,
                                        self.error_text,
                                        self.loading,
                                        self.verify_button,
                                        
                                        ft.Divider(height=20),
                                        
                                        self.resend_button,
                                        
                                        Text(
                                            "💡 Vérifiez vos emails (y compris les spams)",
                                            size=12,
                                            color=AppColors.TEXT_SECONDARY,
                                            text_align=TextAlign.CENTER,
                                            italic=True,
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
    
    def _on_verify(self, e):
        """Vérifie le code MFA saisi."""
        code = self.code_field.value
        
        # Validation
        if not code or len(code) != 6:
            self.error_text.value = "Veuillez entrer un code à 6 chiffres"
            self.page.update()
            return
        
        if not code.isdigit():
            self.error_text.value = "Le code doit contenir uniquement des chiffres"
            self.page.update()
            return
        
        # Afficher le chargement
        self.error_text.value = ""
        self.verify_button.disabled = True
        self.loading.visible = True
        self.page.update()
        
        try:
            user_id = getattr(self.app_state, 'temp_user_id', None)
            
            if not user_id:
                raise APIError("Session expirée. Veuillez vous reconnecter.")
            
            # Appel API pour vérifier le code
            result = api_client.verify_mfa(user_id, code)
            
            # Vérification réussie
            token = result.get('access_token')
            api_client.set_token(token)
            
            # Récupérer le profil
            profile = api_client.get_profile()
            self.app_state.set_user(profile)
            self.app_state.token = token
            
            # Nettoyer les données temporaires
            if hasattr(self.app_state, 'temp_user_id'):
                delattr(self.app_state, 'temp_user_id')
            if hasattr(self.app_state, 'temp_user_email'):
                delattr(self.app_state, 'temp_user_email')
            
            self.page.route = "/dashboard"
            self.page.update()
        
        except APIError as e:
            self.error_text.value = f"Code incorrect : {e.message}"
        except Exception as e:
            self.error_text.value = f"Erreur : {str(e)}"
        finally:
            self.verify_button.disabled = False
            self.loading.visible = False
            self.page.update()
    
    def _on_resend(self, e):
        """Renvoie le code MFA par email."""
        self.resend_button.disabled = True
        self.page.update()
        
        try:
            api_client.resend_mfa()
            
            self.page.open(
                ft.AlertDialog(
                    title=Text("Code renvoyé"),
                    content=Text("Un nouveau code a été envoyé à votre adresse email."),
                    actions=[
                        ft.TextButton("OK", on_click=lambda _: self.page.close(self.page.overlay[-1]))
                    ],
                )
            )
        
        except APIError as e:
            self.page.open(
                ft.AlertDialog(
                    title=Text("Erreur"),
                    content=Text(f"Impossible de renvoyer le code : {e.message}"),
                    actions=[
                        ft.TextButton("OK", on_click=lambda _: self.page.close(self.page.overlay[-1]))
                    ],
                )
            )
        finally:
            self.resend_button.disabled = False
            self.page.update()