"""
Page de gestion des notifications.
Affiche toutes les notifications de l'utilisateur avec options de lecture.
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
    Dropdown,
    dropdown,
    ElevatedButton,
    OutlinedButton,
    ListView,
    ListTile,
    border_radius,
    alignment,
    padding,
)
from frontend.api_client import api_client, APIError
from frontend.theme import AppColors, AppSpacing


class NotificationsPage:
    """Page de gestion des notifications."""
    
    def __init__(self, page: ft.Page, app_state):
        self.page = page
        self.app_state = app_state
        
        # Données
        self.notifications = []
        self.filtered_notifications = []
        
        # Filtres
        self.type_filter = Dropdown(
            label="Type",
            width=180,
            border_radius=border_radius.all(10),
            options=[
                dropdown.Option(key="", text="Tous les types"),
                dropdown.Option(key="INFO", text="ℹ️ Information"),
                dropdown.Option(key="SUCCESS", text="✅ Succès"),
                dropdown.Option(key="WARNING", text="⚠️ Avertissement"),
                dropdown.Option(key="ERROR", text="❌ Erreur"),
            ],
            on_change=self._on_filter_changed,
        )
        
        self.statut_filter = Dropdown(
            label="Statut",
            width=180,
            border_radius=border_radius.all(10),
            options=[
                dropdown.Option(key="", text="Tous les statuts"),
                dropdown.Option(key="non_lues", text="🔵 Non lues"),
                dropdown.Option(key="lues", text="✓ Lues"),
            ],
            on_change=self._on_filter_changed,
        )
        
        # Liste des notifications
        self.notifications_list = ListView(
            expand=True,
            spacing=10,
            padding=10,
        )
        
        # Compteurs
        self.count_text = Text("", size=13, color=AppColors.TEXT_SECONDARY)
        
        # Chargement
        self.loading = ft.ProgressRing(visible=True)
        self.error_text = Text("", color=Colors.RED_400, size=14)
        
        # Bouton marquer tout comme lu
        self.mark_all_read_button = ElevatedButton(
            "✓ Marquer tout comme lu",
            icon=Icons.DONE_ALL,
            bgcolor=AppColors.PRIMARY,
            color=Colors.WHITE,
            on_click=self._mark_all_as_read,
        )
    
    def build(self) -> View:
        """Construit la vue des notifications."""
        
        return View(
            "/notifications",
            [
                self._create_app_bar("Mes Notifications"),
                Container(
                    content=Column(
                        [
                            # En-tête
                            Row(
                                [
                                    Column(
                                        [
                                            Text(
                                                "🔔 Mes Notifications",
                                                size=24,
                                                weight=FontWeight.BOLD,
                                                color=AppColors.TEXT_PRIMARY,
                                            ),
                                            Text(
                                                "Restez informé des dernières mises à jour",
                                                size=13,
                                                color=AppColors.TEXT_SECONDARY,
                                            ),
                                        ],
                                        spacing=5,
                                    ),
                                    Row(
                                        [
                                            self.mark_all_read_button,
                                            IconButton(
                                                Icons.REFRESH,
                                                tooltip="Actualiser",
                                                on_click=lambda _: self._load_notifications(),
                                            ),
                                        ],
                                        spacing=10,
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            
                            Divider(height=20),
                            
                            # Barre de filtres
                            Container(
                                content=Row(
                                    [
                                        Icon(Icons.FILTER_LIST, color=AppColors.PRIMARY),
                                        Text("Filtres :", weight=FontWeight.BOLD, size=14),
                                        self.type_filter,
                                        self.statut_filter,
                                        IconButton(
                                            Icons.CLEAR_ALL,
                                            tooltip="Réinitialiser",
                                            on_click=self._reset_filters,
                                        ),
                                    ],
                                    wrap=True,
                                    spacing=15,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                padding=15,
                                bgcolor=Colors.WHITE,
                                border_radius=border_radius.all(12),
                            ),
                            
                            Divider(height=15),
                            
                            # Compteurs et chargement
                            Row(
                                [
                                    self.count_text,
                                    self.loading,
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            
                            # Message d'erreur
                            self.error_text,
                            
                            # Liste des notifications
                            Container(
                                content=self.notifications_list,
                                expand=True,
                                bgcolor=Colors.WHITE,
                                padding=10,
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
                        expand=True,
                    ),
                    padding=20,
                    expand=True,
                    bgcolor=AppColors.BACKGROUND,
                ),
                self._create_navigation_bar(),
            ],
        )
    
    def _build_notification_card(self, notification: dict) -> Card:
        """Construit une carte pour une notification."""
        notif_type = notification.get('type', 'INFO')
        is_read = notification.get('lue', False)
        
        # Icône et couleur selon le type
        type_config = {
            'INFO': (Icons.INFO, Colors.BLUE),
            'SUCCESS': (Icons.CHECK_CIRCLE, Colors.GREEN),
            'WARNING': (Icons.WARNING, Colors.ORANGE),
            'ERROR': (Icons.ERROR, Colors.RED),
        }
        icon, color = type_config.get(notif_type, (Icons.INFO, Colors.BLUE))
        
        # Opacité si lue
        opacity = 0.6 if is_read else 1.0
        
        # Contenu
        titre = notification.get('titre', 'Notification')
        message = notification.get('message', '')
        date_creation = self._format_datetime(notification.get('date_creation', ''))
        url_lien = notification.get('url_lien', '')
        
        def on_tap(e):
            """Gère le clic sur la notification."""
            # Marquer comme lue
            if not is_read:
                self._mark_as_read(notification)
            
            # Naviguer vers le lien si présent
            if url_lien:
                self.page.route = url_lien
                self.page.update()
        
        return Card(
            content=Container(
                content=Row(
                    [
                        # Icône
                        Container(
                            content=Icon(icon, size=32, color=Colors.WHITE),
                            bgcolor=color,
                            width=60,
                            height=60,
                            border_radius=border_radius.all(30),
                            alignment=alignment.center,
                        ),
                        
                        # Contenu
                        Expanded(
                            content=Column(
                                [
                                    Row(
                                        [
                                            Text(
                                                titre,
                                                size=15,
                                                weight=FontWeight.BOLD if not is_read else FontWeight.NORMAL,
                                                color=AppColors.TEXT_PRIMARY,
                                            ),
                                            Icon(
                                                Icons.CHECK_CIRCLE,
                                                size=16,
                                                color=Colors.GREEN,
                                            ) if is_read else None,
                                        ],
                                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                    ),
                                    Text(
                                        message,
                                        size=13,
                                        color=AppColors.TEXT_SECONDARY,
                                        max_lines=3,
                                    ),
                                    Text(
                                        date_creation,
                                        size=11,
                                        color=AppColors.TEXT_SECONDARY,
                                        italic=True,
                                    ),
                                ],
                                spacing=5,
                            )
                        ),
                        
                        # Bouton d'action si lien présent
                        IconButton(
                            Icons.OPEN_IN_NEW,
                            icon_size=20,
                            tooltip="Ouvrir",
                            on_click=lambda _: self._open_link(url_lien) if url_lien else None,
                            visible=bool(url_lien),
                        ),
                    ],
                    spacing=15,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                padding=15,
                opacity=opacity,
            ),
            elevation=2 if not is_read else 1,
            on_click=on_tap,
        )
    
    def _format_datetime(self, datetime_str: str) -> str:
        """Formate une date et heure au format français."""
        if not datetime_str:
            return "N/A"
        try:
            from datetime import datetime
            if isinstance(datetime_str, str):
                dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            else:
                dt = datetime_str
            return dt.strftime("%d/%m/%Y à %H:%M")
        except:
            return str(datetime_str)
    
    def _mark_as_read(self, notification: dict):
        """Marque une notification comme lue."""
        notif_id = notification.get('id')
        
        try:
            # Appel API pour marquer comme lue
            # Note: Cette méthode devrait être ajoutée à api_client.py
            # Pour l'instant, on met juste à jour localement
            notification['lue'] = True
            
            # Mettre à jour le compteur
            self.app_state.notifications_count = max(0, self.app_state.notifications_count - 1)
            
            # Re-rendre la liste
            self._render_list()
            
        except Exception as e:
            self.error_text.value = f"Erreur : {str(e)}"
            self.page.update()
    
    def _mark_all_as_read(self, e):
        """Marque toutes les notifications comme lues."""
        try:
            # Appel API
            # Note: Cette méthode devrait être ajoutée à api_client.py
            # Pour l'instant, on met juste à jour localement
            for notif in self.notifications:
                notif['lue'] = True
            
            self.app_state.notifications_count = 0
            
            # Re-rendre la liste
            self._render_list()
            
            self.page.open(
                ft.AlertDialog(
                    title=Text("Succès"),
                    content=Text("Toutes les notifications ont été marquées comme lues."),
                    actions=[
                        ft.TextButton("OK", on_click=lambda _: self.page.close(self.page.overlay[-1]))
                    ],
                )
            )
            
        except Exception as e:
            self.page.open(
                ft.AlertDialog(
                    title=Text("Erreur"),
                    content=Text(f"Impossible de marquer les notifications : {str(e)}"),
                    actions=[
                        ft.TextButton("OK", on_click=lambda _: self.page.close(self.page.overlay[-1]))
                    ],
                )
            )
    
    def _open_link(self, url: str):
        """Ouvre un lien."""
        if url:
            self.page.route = url
            self.page.update()
    
    def _on_filter_changed(self, e):
        """Applique les filtres sur la liste des notifications."""
        type_notif = self.type_filter.value or ""
        statut = self.statut_filter.value or ""
        
        filtered = self.notifications
        
        if type_notif:
            filtered = [n for n in filtered if n.get('type') == type_notif]
        
        if statut == "non_lues":
            filtered = [n for n in filtered if not n.get('lue', False)]
        elif statut == "lues":
            filtered = [n for n in filtered if n.get('lue', False)]
        
        self.filtered_notifications = filtered
        self._render_list()
    
    def _reset_filters(self, e):
        """Réinitialise tous les filtres."""
        self.type_filter.value = ""
        self.statut_filter.value = ""
        self.filtered_notifications = self.notifications
        self._render_list()
        self.page.update()
    
    def _render_list(self):
        """Rendu de la liste des notifications."""
        if self.filtered_notifications:
            self.notifications_list.controls = [
                self._build_notification_card(notif) for notif in self.filtered_notifications
            ]
        else:
            self.notifications_list.controls = [
                Container(
                    content=Column(
                        [
                            Icon(Icons.NOTIFICATIONS_NONE, size=64, color=AppColors.TEXT_SECONDARY),
                            Text(
                                "Aucune notification",
                                size=16,
                                color=AppColors.TEXT_SECONDARY,
                                text_align=TextAlign.CENTER,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=15,
                    ),
                    alignment=alignment.center,
                    padding=50,
                )
            ]
        
        # Compteurs
        total = len(self.filtered_notifications)
        non_lues = sum(1 for n in self.filtered_notifications if not n.get('lue', False))
        self.count_text.value = f"Affichage : {total} notification(s) dont {non_lues} non lue(s)"
        
        self.page.update()
    
    def _load_notifications(self):
        """Charge les notifications depuis l'API."""
        self.loading.visible = True
        self.error_text.value = ""
        self.page.update()
        
        try:
            # Récupérer les notifications
            result = api_client.get_notifications(limit=50)
            self.notifications = result.get('notifications', [])
            self.filtered_notifications = self.notifications
            
            # Mettre à jour le compteur global
            self.app_state.notifications_count = result.get('total_non_lues', 0)
            
            # Construire la liste
            self._render_list()
        
        except APIError as e:
            self.error_text.value = f"Erreur de chargement : {e.message}"
        except Exception as e:
            self.error_text.value = f"Erreur : {str(e)}"
        finally:
            self.loading.visible = False
            self.page.update()
    
    def did_mount(self):
        """Appelé quand la page est montée."""
        self._load_notifications()
    
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
                    badge=ft.Badge(
                        text=str(self.app_state.notifications_count) if self.app_state.notifications_count > 0 else None,
                        bgcolor=Colors.RED,
                    ) if self.app_state.notifications_count > 0 else None,
                    on_click=lambda _: None,  # Déjà sur la page
                ),
                PopupMenuButton(
                    content=CircleAvatar(
                        content=Text(first_letter, weight=FontWeight.BOLD),
                        bgcolor=Colors.WHITE,
                        color=AppColors.PRIMARY,
                    ),
                    items=[
                        PopupMenuItem(text="Mon Profil", icon=Icons.PERSON, on_click=lambda _: self.page.go("/profile")),
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