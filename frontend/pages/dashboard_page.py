"""
Page du tableau de bord principal.
Affiche les statistiques et informations clés selon le rôle de l'utilisateur.
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
    PopupMenuButton,
    PopupMenuItem,
    CircleAvatar,
    NavigationBar,
    NavigationBarDestination,
    border_radius,
    alignment,
    padding,
)
from frontend.api_client import api_client, APIError
from frontend.theme import AppColors, AppSpacing, AppComponents, AppTypography


class DashboardPage:
    """Page du tableau de bord principal."""
    
    def __init__(self, page: ft.Page, app_state):
        self.page = page
        self.app_state = app_state
        self.stats_data = {}
        
        # Composants de statistiques
        self.total_caveaux_card = self._create_stat_card(
            "Total Caveaux", "0", Icons.LOCATION_CITY, Colors.BLUE, "total_caveaux"
        )
        self.disponibles_card = self._create_stat_card(
            "Disponibles", "0", Icons.CHECK_CIRCLE, Colors.GREEN, "caveaux_disponibles"
        )
        self.occupes_card = self._create_stat_card(
            "Occupés", "0", Icons.BUSY, Colors.RED, "caveaux_occupes"
        )
        self.taux_occupation_card = self._create_stat_card(
            "Taux Occupation", "0%", Icons.PIE_CHART, Colors.ORANGE, "taux_occupation"
        )
        
        # Composants pour les concessions
        self.concessions_actives_card = self._create_stat_card(
            "Concessions Actives", "0", Icons.DESCRIPTION, Colors.PURPLE, "concessions_actives"
        )
        self.expiring_soon_card = self._create_stat_card(
            "À Expirer Bientôt", "0", Icons.WARNING, Colors.DEEP_ORANGE, "concessions_expiring_soon"
        )
        
        # Composants pour les finances (admin uniquement)
        self.revenus_mois_card = self._create_stat_card(
            "Revenus du Mois", "0 FC", Icons.ACCOUNT_BALANCE, Colors.TEAL, "revenus_mois"
        )
        self.revenus_annee_card = self._create_stat_card(
            "Revenus de l'Année", "0 FC", Icons.TRENDING_UP, Colors.INDIGO, "revenus_annee"
        )
        
        # Indicateur de chargement
        self.loading = ft.ProgressRing(visible=True)
        self.error_text = Text("", color=Colors.RED_400, size=14)
    
    def _create_stat_card(self, title: str, value: str, icon: str, color: str, stat_key: str) -> Card:
        """Crée une carte de statistique."""
        return Card(
            content=Container(
                content=Column(
                    [
                        Icon(icon, size=40, color=color),
                        Text(value, size=28, weight=FontWeight.BOLD, key=f"value_{stat_key}"),
                        Text(title, size=13, color=AppColors.TEXT_SECONDARY),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10,
                ),
                padding=20,
                width=220,
                height=160,
                border_radius=border_radius.all(12),
            ),
            elevation=3,
        )
    
    def _update_stat_value(self, card: Card, stat_key: str, value: str):
        """Met à jour la valeur d'une carte de statistique."""
        try:
            # Trouver le Text avec la clé correspondante
            for control in card.content.content.controls:
                if hasattr(control, 'key') and control.key == f"value_{stat_key}":
                    control.value = value
                    break
        except Exception:
            pass
    
    def build(self) -> View:
        """Construit la vue du tableau de bord."""
        
        user = self.app_state.user or {}
        user_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
        role = user.get('role', 'CLIENT')
        
        # Contenu principal
        content_controls = [
            # En-tête de bienvenue
            Row(
                [
                    Column(
                        [
                            Text(
                                f"Bonjour, {user_name or 'Utilisateur'} 👋",
                                size=28,
                                weight=FontWeight.BOLD,
                                color=AppColors.TEXT_PRIMARY,
                            ),
                            Text(
                                f"Rôle : {self._get_role_display(role)}",
                                size=14,
                                color=AppColors.TEXT_SECONDARY,
                            ),
                        ],
                        spacing=5,
                    ),
                    Row(
                        [
                            IconButton(
                                Icons.REFRESH,
                                tooltip="Actualiser",
                                on_click=self._load_stats,
                            ),
                        ]
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            
            Divider(height=30),
            
            # Section : Statistiques des caveaux
            Text(
                "📊 Statistiques du Cimetière",
                size=20,
                weight=FontWeight.BOLD,
                color=AppColors.TEXT_PRIMARY,
            ),
            Text(
                "Vue d'ensemble de l'occupation du cimetière",
                size=13,
                color=AppColors.TEXT_SECONDARY,
            ),
            
            Row(
                [
                    self.total_caveaux_card,
                    self.disponibles_card,
                    self.occupes_card,
                    self.taux_occupation_card,
                ],
                wrap=True,
                spacing=20,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            
            Divider(height=30),
        ]
        
        # Section : Concessions (visible pour tous sauf peut-être certains rôles)
        content_controls.extend([
            Text(
                "📜 Gestion des Concessions",
                size=20,
                weight=FontWeight.BOLD,
                color=AppColors.TEXT_PRIMARY,
            ),
            Row(
                [
                    self.concessions_actives_card,
                    self.expiring_soon_card,
                ],
                wrap=True,
                spacing=20,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            
            Divider(height=30),
        ])
        
        # Section : Finances (admin uniquement)
        if role in ['ADMIN']:
            content_controls.extend([
                Text(
                    "💰 Statistiques Financières",
                    size=20,
                    weight=FontWeight.BOLD,
                    color=AppColors.TEXT_PRIMARY,
                ),
                Row(
                    [
                        self.revenus_mois_card,
                        self.revenus_annee_card,
                    ],
                    wrap=True,
                    spacing=20,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                
                Divider(height=30),
            ])
        
        # Section : Actions rapides
        content_controls.extend([
            Text(
                "⚡ Actions Rapides",
                size=20,
                weight=FontWeight.BOLD,
                color=AppColors.TEXT_PRIMARY,
            ),
            Row(
                self._get_quick_actions(role),
                wrap=True,
                spacing=15,
                alignment=ft.MainAxisAlignment.START,
            ),
            
            Divider(height=20),
            
            # Indicateur de chargement et erreurs
            self.loading,
            self.error_text,
        ])
        
        return View(
            "/dashboard",
            [
                self._create_app_bar("Tableau de Bord"),
                Container(
                    content=Column(
                        content_controls,
                        spacing=10,
                    ),
                    padding=20,
                    expand=True,
                    bgcolor=AppColors.BACKGROUND,
                ),
                self._create_navigation_bar(),
            ],
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
    
    def _get_quick_actions(self, role: str) -> list:
        """Retourne les actions rapides selon le rôle."""
        actions = []
        
        # Action commune : Voir la carte
        actions.append(
            ft.ElevatedButton(
                "🗺️ Voir la Carte",
                icon=Icons.MAP,
                on_click=lambda _: self.page.go("/carte"),
                bgcolor=AppColors.PRIMARY,
                color=Colors.WHITE,
            )
        )
        
        # Actions selon le rôle
        if role in ['CLIENT']:
            actions.append(
                ft.ElevatedButton(
                    "📝 Mes Réservations",
                    icon=Icons.BOOKMARK,
                    on_click=lambda _: self.page.go("/reservations"),
                    bgcolor=Colors.BLUE,
                    color=Colors.WHITE,
                )
            )
            actions.append(
                ft.ElevatedButton(
                    "💳 Mes Factures",
                    icon=Icons.RECEIPT,
                    on_click=lambda _: self.page.go("/factures"),
                    bgcolor=Colors.ORANGE,
                    color=Colors.WHITE,
                )
            )
        
        if role in ['ADMIN', 'SECRETARY']:
            actions.append(
                ft.ElevatedButton(
                    "📋 Concessions",
                    icon=Icons.DESCRIPTION,
                    on_click=lambda _: self.page.go("/concessions"),
                    bgcolor=Colors.PURPLE,
                    color=Colors.WHITE,
                )
            )
        
        if role in ['ADMIN']:
            actions.append(
                ft.ElevatedButton(
                    "📊 Rapports",
                    icon=Icons.ANALYTICS,
                    on_click=lambda _: self._show_message("Rapports", "Fonctionnalité à venir"),
                    bgcolor=Colors.TEAL,
                    color=Colors.WHITE,
                )
            )
        
        return actions
    
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
                    badge=ft.Badge(
                        text=str(self.app_state.notifications_count) if self.app_state.notifications_count > 0 else None,
                        bgcolor=Colors.RED,
                    ) if self.app_state.notifications_count > 0 else None,
                    on_click=lambda _: self.page.go("/notifications"),
                ),
                PopupMenuButton(
                    content=CircleAvatar(
                        content=Text(first_letter, weight=FontWeight.BOLD),
                        bgcolor=Colors.WHITE,
                        color=AppColors.PRIMARY,
                    ),
                    items=[
                        PopupMenuItem(
                            text="Mon Profil",
                            icon=Icons.PERSON,
                            on_click=lambda _: self.page.go("/profile"),
                        ),
                        PopupMenuItem(),
                        PopupMenuItem(
                            text="Déconnexion",
                            icon=Icons.LOGOUT,
                            on_click=on_logout,
                        ),
                    ],
                ),
            ],
        )
    
    def _create_navigation_bar(self) -> NavigationBar:
        """Crée la barre de navigation inférieure."""
        
        def handle_change(e):
            routes = ["/dashboard", "/carte", "/reservations", "/factures"]
            selected_index = e.control.selected_index
            if 0 <= selected_index < len(routes):
                self.page.route = routes[selected_index]
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
    
    def did_mount(self):
        """Appelé quand la page est montée - charge les statistiques."""
        self._load_stats(None)
    
    def _load_stats(self, e):
        """Charge les statistiques depuis l'API."""
        self.loading.visible = True
        self.error_text.value = ""
        self.page.update()
        
        try:
            # Charger les statistiques du cimetière
            stats = api_client.get_statistiques()
            self.stats_data = stats
            
            # Mettre à jour les cartes
            self._update_stat_value(self.total_caveaux_card, "total_caveaux", str(stats.get('total_caveaux', 0)))
            self._update_stat_value(self.disponibles_card, "caveaux_disponibles", str(stats.get('caveaux_disponibles', 0)))
            self._update_stat_value(self.occupes_card, "caveaux_occupes", str(stats.get('caveaux_occupes', 0)))
            self._update_stat_value(
                self.taux_occupation_card, 
                "taux_occupation", 
                f"{stats.get('taux_occupation', 0):.1f}%"
            )
            self._update_stat_value(self.concessions_actives_card, "concessions_actives", str(stats.get('concessions_actives', 0)))
            self._update_stat_value(self.expiring_soon_card, "concessions_expiring_soon", str(stats.get('concessions_expiring_soon', 0)))
            
            # Statistiques financières (admin)
            if self.app_state.user and self.app_state.user.get('role') == 'ADMIN':
                self._update_stat_value(
                    self.revenus_mois_card, 
                    "revenus_mois", 
                    f"{stats.get('revenus_mois', 0):,.0f} FC"
                )
                self._update_stat_value(
                    self.revenus_annee_card, 
                    "revenus_annee", 
                    f"{stats.get('revenus_annee', 0):,.0f} FC"
                )
            
            # Charger le nombre de notifications
            try:
                notif_count = api_client.compter_notifications_non_lues()
                self.app_state.notifications_count = notif_count
            except Exception:
                pass
            
        except APIError as e:
            self.error_text.value = f"Erreur de chargement : {e.message}"
        except Exception as e:
            self.error_text.value = f"Erreur : {str(e)}"
        finally:
            self.loading.visible = False
            self.page.update()
    
    def _show_message(self, title: str, message: str):
        """Affiche un message dans une boîte de dialogue."""
        self.page.open(
            ft.AlertDialog(
                title=Text(title),
                content=Text(message),
                actions=[
                    ft.TextButton("OK", on_click=lambda _: self.page.close(self.page.overlay[-1]))
                ],
            )
        )