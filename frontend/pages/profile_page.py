"""
Page de profil utilisateur.
Permet de consulter et modifier ses informations personnelles.
"""
import flet as ft
from flet import (
    View,
    AppBar,
    Container,
    Column,
    Row,
    Text,
    Icon,
    Icons,
    Colors,
    FontWeight,
    TextAlign,
    Card,
    Divider,
    IconButton,
    CircleAvatar,
    NavigationBar,
    NavigationBarDestination,
    PopupMenuButton,
    PopupMenuItem,
    TextField,
    ElevatedButton,
    OutlinedButton,
    Tabs,
    Tab,
    border_radius,
    alignment,
    padding,
)
from frontend.api_client import api_client, APIError
from frontend.theme import AppColors, AppSpacing


class ProfilePage:
    """Page de profil utilisateur."""
    
    def __init__(self, page: ft.Page, app_state):
        self.page = page
        self.app_state = app_state
        
        # Champs du formulaire de profil
        self.first_name_field = TextField(
            label="Prénom",
            prefix_icon=Icons.PERSON,
            border_radius=border_radius.all(10),
        )
        
        self.last_name_field = TextField(
            label="Nom",
            prefix_icon=Icons.PERSON,
            border_radius=border_radius.all(10),
        )
        
        self.email_field = TextField(
            label="Email",
            prefix_icon=Icons.EMAIL,
            border_radius=border_radius.all(10),
            disabled=True,  # L'email ne peut pas être modifié
        )
        
        self.phone_field = TextField(
            label="Téléphone",
            prefix_icon=Icons.PHONE,
            border_radius=border_radius.all(10),
        )
        
        self.address_field = TextField(
            label="Adresse",
            prefix_icon=Icons.HOME,
            border_radius=border_radius.all(10),
            multiline=True,
            min_lines=2,
            max_lines=4,
        )
        
        self.national_id_field = TextField(
            label="N° Identité Nationale",
            prefix_icon=Icons.BADGE,
            border_radius=border_radius.all(10),
            disabled=True,  # Ne peut pas être modifié
        )
        
        # Champs pour le changement de mot de passe
        self.old_password_field = TextField(
            label="Ancien mot de passe",
            password=True,
            can_reveal_password=True,
            prefix_icon=Icons.LOCK,
            border_radius=border_radius.all(10),
        )
        
        self.new_password_field = TextField(
            label="Nouveau mot de passe",
            password=True,
            can_reveal_password=True,
            prefix_icon=Icons.LOCK_OUTLINE,
            border_radius=border_radius.all(10),
        )
        
        self.confirm_password_field = TextField(
            label="Confirmer le nouveau mot de passe",
            password=True,
            can_reveal_password=True,
            prefix_icon=Icons.LOCK_RESET,
            border_radius=border_radius.all(10),
        )
        
        # Messages
        self.profile_message = Text("", size=13, text_align=TextAlign.CENTER)
        self.password_message = Text("", size=13, text_align=TextAlign.CENTER)
        
        # Indicateurs de chargement
        self.profile_loading = ft.ProgressRing(visible=False)
        self.password_loading = ft.ProgressRing(visible=False)
        
        # Statistiques personnelles
        self.stats_container = Container()
    
    def build(self) -> View:
        """Construit la vue du profil."""
        
        user = self.app_state.user or {}
        role = user.get('role', 'CLIENT')
        role_display = self._get_role_display(role)
        role_color = self._get_role_color(role)
        
        return View(
            "/profile",
            [
                self._create_app_bar("Mon Profil"),
                Container(
                    content=Column(
                        [
                            # En-tête avec avatar
                            Container(
                                content=Column(
                                    [
                                        CircleAvatar(
                                            content=Text(
                                                (user.get('first_name') or 'U')[0].upper(),
                                                size=40,
                                                weight=FontWeight.BOLD,
                                            ),
                                            radius=50,
                                            bgcolor=AppColors.PRIMARY,
                                            color=Colors.WHITE,
                                        ),
                                        Text(
                                            f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or "Utilisateur",
                                            size=24,
                                            weight=FontWeight.BOLD,
                                            color=AppColors.TEXT_PRIMARY,
                                        ),
                                        Container(
                                            content=Text(
                                                role_display,
                                                size=12,
                                                weight=FontWeight.BOLD,
                                                color=Colors.WHITE,
                                            ),
                                            bgcolor=role_color,
                                            padding=ft.padding.symmetric(horizontal=15, vertical=5),
                                            border_radius=border_radius.all(20),
                                        ),
                                        Text(
                                            user.get('email', ''),
                                            size=14,
                                            color=AppColors.TEXT_SECONDARY,
                                        ),
                                    ],
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    spacing=10,
                                ),
                                padding=30,
                                bgcolor=Colors.WHITE,
                                border_radius=border_radius.all(15),
                                shadow=ft.BoxShadow(
                                    spread_radius=1,
                                    blur_radius=10,
                                    color=Colors.with_opacity(0.1, Colors.BLACK),
                                    offset=ft.Offset(0, 3),
                                ),
                            ),
                            
                            Divider(height=20),
                            
                            # Onglets : Informations / Sécurité / Statistiques
                            Tabs(
                                tabs=[
                                    ft.Tab(
                                        text="Informations",
                                        icon=Icons.PERSON,
                                        content=self._build_info_tab(),
                                    ),
                                    ft.Tab(
                                        text="Sécurité",
                                        icon=Icons.SECURITY,
                                        content=self._build_security_tab(),
                                    ),
                                    ft.Tab(
                                        text="Statistiques",
                                        icon=Icons.ANALYTICS,
                                        content=self._build_stats_tab(),
                                    ),
                                ],
                                expand=True,
                            ),
                        ],
                        spacing=10,
                        expand=True,
                    ),
                    padding=20,
                    expand=True,
                    bgcolor=AppColors.BACKGROUND,
                ),
                self._create_navigation_bar(),
            ],
        )
    
    def _build_info_tab(self) -> Container:
        """Construit l'onglet des informations personnelles."""
        return Container(
            content=Column(
                [
                    Text(
                        "📝 Informations personnelles",
                        size=18,
                        weight=FontWeight.BOLD,
                        color=AppColors.TEXT_PRIMARY,
                    ),
                    Text(
                        "Modifiez vos informations de contact",
                        size=13,
                        color=AppColors.TEXT_SECONDARY,
                    ),
                    
                    Divider(height=20),
                    
                    # Formulaire
                    Container(
                        content=Column(
                            [
                                Row(
                                    [
                                        self.first_name_field,
                                        self.last_name_field,
                                    ],
                                    spacing=15,
                                ),
                                self.email_field,
                                self.phone_field,
                                self.address_field,
                                self.national_id_field,
                                
                                Divider(height=15),
                                
                                self.profile_message,
                                self.profile_loading,
                                
                                ElevatedButton(
                                    "💾 Enregistrer les modifications",
                                    icon=Icons.SAVE,
                                    bgcolor=AppColors.PRIMARY,
                                    color=Colors.WHITE,
                                    width=300,
                                    on_click=self._update_profile,
                                ),
                            ],
                            spacing=15,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        padding=25,
                        bgcolor=Colors.WHITE,
                        border_radius=border_radius.all(12),
                        shadow=ft.BoxShadow(
                            spread_radius=1,
                            blur_radius=8,
                            color=Colors.with_opacity(0.1, Colors.BLACK),
                            offset=ft.Offset(0, 3),
                        ),
                    ),
                ],
                spacing=10,
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=20,
            expand=True,
        )
    
    def _build_security_tab(self) -> Container:
        """Construit l'onglet de sécurité."""
        user = self.app_state.user or {}
        mfa_enabled = user.get('mfa_enabled', False)
        
        return Container(
            content=Column(
                [
                    Text(
                        "🔒 Sécurité du compte",
                        size=18,
                        weight=FontWeight.BOLD,
                        color=AppColors.TEXT_PRIMARY,
                    ),
                    Text(
                        "Gérez votre mot de passe et la sécurité",
                        size=13,
                        color=AppColors.TEXT_SECONDARY,
                    ),
                    
                    Divider(height=20),
                    
                    # Informations de sécurité
                    Container(
                        content=Column(
                            [
                                Row(
                                    [
                                        Icon(
                                            Icons.SECURITY,
                                            color=AppColors.SUCCESS if mfa_enabled else Colors.ORANGE,
                                            size=32,
                                        ),
                                        Column(
                                            [
                                                Text(
                                                    "Authentification à double facteur (MFA)",
                                                    size=14,
                                                    weight=FontWeight.BOLD,
                                                ),
                                                Text(
                                                    "Activée" if mfa_enabled else "Désactivée",
                                                    size=12,
                                                    color=AppColors.TEXT_SECONDARY,
                                                ),
                                            ],
                                            spacing=3,
                                        ),
                                    ],
                                    spacing=15,
                                ),
                            ],
                            spacing=10,
                        ),
                        padding=20,
                        bgcolor=Colors.WHITE,
                        border_radius=border_radius.all(12),
                        shadow=ft.BoxShadow(
                            spread_radius=1,
                            blur_radius=5,
                            color=Colors.with_opacity(0.1, Colors.BLACK),
                            offset=ft.Offset(0, 2),
                        ),
                    ),
                    
                    Divider(height=20),
                    
                    # Formulaire de changement de mot de passe
                    Container(
                        content=Column(
                            [
                                Text(
                                    "🔑 Changer le mot de passe",
                                    size=16,
                                    weight=FontWeight.BOLD,
                                ),
                                
                                self.old_password_field,
                                self.new_password_field,
                                self.confirm_password_field,
                                
                                Divider(height=15),
                                
                                self.password_message,
                                self.password_loading,
                                
                                ElevatedButton(
                                    "🔐 Changer le mot de passe",
                                    icon=Icons.LOCK_RESET,
                                    bgcolor=AppColors.PRIMARY,
                                    color=Colors.WHITE,
                                    width=300,
                                    on_click=self._change_password,
                                ),
                            ],
                            spacing=15,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        padding=25,
                        bgcolor=Colors.WHITE,
                        border_radius=border_radius.all(12),
                        shadow=ft.BoxShadow(
                            spread_radius=1,
                            blur_radius=8,
                            color=Colors.with_opacity(0.1, Colors.BLACK),
                            offset=ft.Offset(0, 3),
                        ),
                    ),
                ],
                spacing=10,
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=20,
            expand=True,
        )
    
    def _build_stats_tab(self) -> Container:
        """Construit l'onglet des statistiques personnelles."""
        return Container(
            content=Column(
                [
                    Text(
                        "📊 Mes Statistiques",
                        size=18,
                        weight=FontWeight.BOLD,
                        color=AppColors.TEXT_PRIMARY,
                    ),
                    Text(
                        "Vue d'ensemble de votre activité",
                        size=13,
                        color=AppColors.TEXT_SECONDARY,
                    ),
                    
                    Divider(height=20),
                    
                    # Cartes de statistiques
                    Row(
                        [
                            self._create_stat_card(
                                "Mes Réservations",
                                "0",
                                Icons.BOOKMARK,
                                Colors.BLUE,
                            ),
                            self._create_stat_card(
                                "Mes Factures",
                                "0",
                                Icons.RECEIPT,
                                Colors.ORANGE,
                            ),
                        ],
                        wrap=True,
                        spacing=15,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    
                    Divider(height=20),
                    
                    # Informations du compte
                    Container(
                        content=Column(
                            [
                                Text(
                                    "ℹ️ Informations du compte",
                                    size=16,
                                    weight=FontWeight.BOLD,
                                ),
                                self._info_row("Membre depuis", self._format_date((self.app_state.user or {}).get('date_joined', ''))),
                                self._info_row("Dernière connexion", "Récemment"),
                                self._info_row("Statut du compte", "Actif"),
                            ],
                            spacing=10,
                        ),
                        padding=20,
                        bgcolor=Colors.WHITE,
                        border_radius=border_radius.all(12),
                        shadow=ft.BoxShadow(
                            spread_radius=1,
                            blur_radius=5,
                            color=Colors.with_opacity(0.1, Colors.BLACK),
                            offset=ft.Offset(0, 2),
                        ),
                    ),
                ],
                spacing=10,
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=20,
            expand=True,
        )
    
    def _create_stat_card(self, title: str, value: str, icon: str, color: str) -> Card:
        """Crée une carte de statistique."""
        return Card(
            content=Container(
                content=Column(
                    [
                        Icon(icon, size=40, color=color),
                        Text(value, size=28, weight=FontWeight.BOLD),
                        Text(title, size=13, color=AppColors.TEXT_SECONDARY),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10,
                ),
                padding=20,
                width=200,
                height=150,
                border_radius=border_radius.all(12),
            ),
            elevation=3,
        )
    
    def _info_row(self, label: str, value: str) -> Row:
        """Crée une ligne d'information."""
        return Row(
            [
                Text(f"{label} :", size=13, color=AppColors.TEXT_SECONDARY, width=150),
                Text(value, size=13, weight=FontWeight.W_500),
            ],
            spacing=10,
        )
    
    def _get_role_display(self, role: str) -> str:
        """Retourne l'affichage du rôle."""
        roles = {
            'ADMIN': 'Administrateur',
            'FIELD_AGENT': 'Agent de terrain',
            'SECRETARY': 'Secrétariat',
            'CLIENT': 'Client',
        }
        return roles.get(role, role)
    
    def _get_role_color(self, role: str) -> str:
        """Retourne la couleur associée au rôle."""
        colors = {
            'ADMIN': AppColors.ROLE_ADMIN,
            'FIELD_AGENT': AppColors.ROLE_AGENT,
            'SECRETARY': AppColors.ROLE_SECRETARY,
            'CLIENT': AppColors.ROLE_CLIENT,
        }
        return colors.get(role, AppColors.TEXT_SECONDARY)
    
    def _format_date(self, date_str: str) -> str:
        """Formate une date au format français."""
        if not date_str:
            return "N/A"
        try:
            from datetime import datetime
            if isinstance(date_str, str):
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                dt = date_str
            return dt.strftime("%d/%m/%Y")
        except:
            return str(date_str)
    
    def _update_profile(self, e):
        """Met à jour le profil utilisateur."""
        # Validation
        if not self.first_name_field.value or not self.last_name_field.value:
            self.profile_message.value = "❌ Le prénom et le nom sont obligatoires"
            self.profile_message.color = Colors.RED_400
            self.page.update()
            return
        
        # Afficher le chargement
        self.profile_message.value = ""
        self.profile_loading.visible = True
        self.page.update()
        
        try:
            # Appel API
            result = api_client.update_profile(
                first_name=self.first_name_field.value,
                last_name=self.last_name_field.value,
                phone=self.phone_field.value or '',
                address=self.address_field.value or '',
            )
            
            # Mettre à jour l'état local
            if self.app_state.user:
                self.app_state.user['first_name'] = self.first_name_field.value
                self.app_state.user['last_name'] = self.last_name_field.value
                self.app_state.user['phone'] = self.phone_field.value or ''
                self.app_state.user['address'] = self.address_field.value or ''
            
            self.profile_message.value = "✅ Profil mis à jour avec succès"
            self.profile_message.color = AppColors.SUCCESS
            
            self.page.open(
                ft.AlertDialog(
                    title=Text("Succès"),
                    content=Text("Votre profil a été mis à jour avec succès."),
                    actions=[
                        ft.TextButton("OK", on_click=lambda _: self.page.close(self.page.overlay[-1]))
                    ],
                )
            )
        
        except APIError as e:
            self.profile_message.value = f"❌ Erreur : {e.message}"
            self.profile_message.color = Colors.RED_400
        except Exception as e:
            self.profile_message.value = f"❌ Erreur : {str(e)}"
            self.profile_message.color = Colors.RED_400
        finally:
            self.profile_loading.visible = False
            self.page.update()
    
    def _change_password(self, e):
        """Change le mot de passe."""
        old_password = self.old_password_field.value
        new_password = self.new_password_field.value
        confirm_password = self.confirm_password_field.value
        
        # Validation
        if not old_password or not new_password or not confirm_password:
            self.password_message.value = "❌ Tous les champs sont obligatoires"
            self.password_message.color = Colors.RED_400
            self.page.update()
            return
        
        if new_password != confirm_password:
            self.password_message.value = "❌ Les mots de passe ne correspondent pas"
            self.password_message.color = Colors.RED_400
            self.page.update()
            return
        
        if len(new_password) < 8:
            self.password_message.value = "❌ Le mot de passe doit contenir au moins 8 caractères"
            self.password_message.color = Colors.RED_400
            self.page.update()
            return
        
        # Afficher le chargement
        self.password_message.value = ""
        self.password_loading.visible = True
        self.page.update()
        
        try:
            # Appel API
            api_client.change_password(old_password, new_password)
            
            # Réinitialiser les champs
            self.old_password_field.value = ""
            self.new_password_field.value = ""
            self.confirm_password_field.value = ""
            
            self.password_message.value = "✅ Mot de passe changé avec succès"
            self.password_message.color = AppColors.SUCCESS
            
            self.page.open(
                ft.AlertDialog(
                    title=Text("Succès"),
                    content=Text("Votre mot de passe a été changé avec succès."),
                    actions=[
                        ft.TextButton("OK", on_click=lambda _: self.page.close(self.page.overlay[-1]))
                    ],
                )
            )
        
        except APIError as e:
            self.password_message.value = f"❌ Erreur : {e.message}"
            self.password_message.color = Colors.RED_400
        except Exception as e:
            self.password_message.value = f"❌ Erreur : {str(e)}"
            self.password_message.color = Colors.RED_400
        finally:
            self.password_loading.visible = False
            self.page.update()
    
    def _load_profile(self):
        """Charge les données du profil."""
        user = self.app_state.user or {}
        
        # Remplir les champs
        self.first_name_field.value = user.get('first_name', '')
        self.last_name_field.value = user.get('last_name', '')
        self.email_field.value = user.get('email', '')
        self.phone_field.value = user.get('phone', '')
        self.address_field.value = user.get('address', '')
        self.national_id_field.value = user.get('national_id', '')
        
        self.page.update()
    
    def did_mount(self):
        """Appelé quand la page est montée."""
        self._load_profile()
    
    # === COMPOSANTS COMMUNS ===
    
    def _create_app_bar(self, title: str) -> AppBar:
        """Crée la barre d'application."""
        def on_logout(e):
            api_client.clear_token()
            self.app_state.clear_user()
            self.page.route = "/login"
            self.page.update()
        
        user = self.app_state.user or {}
        first_letter = (user.get('first_name') or 'U')[0].upper()
        
        return AppBar(
            title=Text(title),
            center_title=True,
            bgcolor=AppColors.PRIMARY,
            color=Colors.WHITE,
            actions=[
                IconButton(
                    Icons.NOTIFICATIONS,
                    on_click=lambda _: self.page.go("/notifications"),
                ),
                PopupMenuButton(
                    content=CircleAvatar(
                        content=Text(first_letter, weight=FontWeight.BOLD),
                        bgcolor=Colors.WHITE,
                        color=AppColors.PRIMARY,
                    ),
                    items=[
                        PopupMenuItem(text="Tableau de bord", icon=Icons.DASHBOARD, on_click=lambda _: self.page.go("/dashboard")),
                        PopupMenuItem(),
                        PopupMenuItem(text="Déconnexion", icon=Icons.LOGOUT, on_click=on_logout),
                    ],
                ),
            ],
        )
    
    def _create_navigation_bar(self) -> NavigationBar:
        """Crée la barre de navigation inférieure."""
        def handle_change(e):
            routes = ["/dashboard", "/carte", "/reservations", "/factures"]
            idx = e.control.selected_index
            if 0 <= idx < len(routes):
                self.page.route = routes[idx]
                self.page.update()
        
        return NavigationBar(
            destinations=[
                NavigationBarDestination(icon=Icons.DASHBOARD, label="Accueil"),
                NavigationBarDestination(icon=Icons.MAP, label="Carte"),
                NavigationBarDestination(icon=Icons.BOOKMARK, label="Réservations"),
                NavigationBarDestination(icon=Icons.RECEIPT, label="Factures"),
            ],
            on_change=handle_change,
            bgcolor=Colors.WHITE,
        )