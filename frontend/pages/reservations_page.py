"""
Page de gestion des réservations.
Affiche les réservations de l'utilisateur connecté avec leurs statuts.
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
    DataTable,
    DataColumn,
    DataCell,
    DataRow,
    border_radius,
    alignment,
    padding,
)
from frontend.api_client import api_client, APIError
from frontend.theme import AppColors, AppSpacing


class ReservationsPage:
    """Page de gestion des réservations."""
    
    def __init__(self, page: ft.Page, app_state):
        self.page = page
        self.app_state = app_state
        
        # Données
        self.reservations = []
        
        # Tableau des réservations
        self.reservations_table = DataTable(
            columns=[
                DataColumn(Text("N° Contrat")),
                DataColumn(Text("Caveau")),
                DataColumn(Text("Type")),
                DataColumn(Text("Date début")),
                DataColumn(Text("Date fin")),
                DataColumn(Text("Statut")),
                DataColumn(Text("Actions")),
            ],
            rows=[],
            border=ft.border.all(1, AppColors.DIVIDER),
            border_radius=border_radius.all(10),
            horizontal_lines=ft.BorderSide(1, AppColors.DIVIDER),
            heading_row_color=AppColors.PRIMARY,
            heading_row_height=50,
            data_row_height=60,
        )
        
        # Chargement
        self.loading = ft.ProgressRing(visible=True)
        self.error_text = Text("", color=Colors.RED_400, size=14)
        self.empty_text = Text(
            "Aucune réservation pour le moment",
            size=16,
            color=AppColors.TEXT_SECONDARY,
            text_align=TextAlign.CENTER,
        )
    
    def build(self) -> View:
        """Construit la vue des réservations."""
        
        return View(
            "/reservations",
            [
                self._create_app_bar("Mes Réservations"),
                Container(
                    content=Column(
                        [
                            # En-tête
                            Row(
                                [
                                    Column(
                                        [
                                            Text(
                                                "📝 Mes Réservations",
                                                size=24,
                                                weight=FontWeight.BOLD,
                                                color=AppColors.TEXT_PRIMARY,
                                            ),
                                            Text(
                                                "Historique et suivi de vos réservations",
                                                size=13,
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
                                                on_click=lambda _: self._load_reservations(),
                                            ),
                                        ]
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            
                            Divider(height=20),
                            
                            # Indicateur de chargement
                            self.loading,
                            
                            # Message d'erreur
                            self.error_text,
                            
                            # Contenu principal
                            Container(
                                content=self.reservations_table,
                                expand=True,
                                bgcolor=Colors.WHITE,
                                padding=20,
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
    
    def _build_reservation_row(self, reservation: dict) -> DataRow:
        """Construit une ligne du tableau pour une réservation."""
        statut = reservation.get('statut', 'ACTIVE')
        statut_display = reservation.get('statut_display', statut)
        
        # Couleur du statut
        statut_colors = {
            'ACTIVE': AppColors.SUCCESS,
            'EXPIREE': AppColors.ERROR,
            'RESILIEE': AppColors.TEXT_SECONDARY,
            'RENOUVELEE': Colors.BLUE,
        }
        statut_color = statut_colors.get(statut, AppColors.TEXT_SECONDARY)
        
        # Date de fin
        date_fin = reservation.get('date_fin')
        date_fin_text = self._format_date(date_fin) if date_fin else "Perpétuelle"
        
        # Jours restants
        jours_restants = reservation.get('jours_restants')
        if jours_restants is not None and jours_restants > 0:
            date_fin_text += f"\n({jours_restants} jours)"
        
        return DataRow(
            cells=[
                DataCell(
                    Text(
                        reservation.get('numero_contrat', 'N/A'),
                        weight=FontWeight.BOLD,
                        size=13,
                    )
                ),
                DataCell(
                    Text(
                        reservation.get('caveau_code', 'N/A'),
                        size=13,
                    )
                ),
                DataCell(
                    Text(
                        reservation.get('type_concession', 'N/A').replace('_', ' ').title(),
                        size=13,
                    )
                ),
                DataCell(
                    Text(
                        self._format_date(reservation.get('date_debut')),
                        size=13,
                    )
                ),
                DataCell(
                    Text(
                        date_fin_text,
                        size=12,
                    )
                ),
                DataCell(
                    Container(
                        content=Text(
                            statut_display,
                            size=11,
                            weight=FontWeight.BOLD,
                            color=Colors.WHITE,
                        ),
                        bgcolor=statut_color,
                        padding=ft.padding.symmetric(horizontal=12, vertical=5),
                        border_radius=border_radius.all(15),
                    )
                ),
                DataCell(
                    Row(
                        [
                            IconButton(
                                Icons.VISIBILITY,
                                icon_size=18,
                                tooltip="Voir les détails",
                                on_click=lambda _, r=reservation: self._show_details(r),
                            ),
                        ],
                        spacing=0,
                    )
                ),
            ]
        )
    
    def _format_date(self, date_str: str) -> str:
        """Formate une date au format français."""
        if not date_str:
            return "N/A"
        try:
            from datetime import datetime
            if isinstance(date_str, str):
                date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                date = date_str
            return date.strftime("%d/%m/%Y")
        except:
            return str(date_str)
    
    def _show_details(self, reservation: dict):
        """Affiche les détails d'une réservation."""
        statut = reservation.get('statut', 'ACTIVE')
        statut_display = reservation.get('statut_display', statut)
        
        # Couleur du statut
        statut_colors = {
            'ACTIVE': AppColors.SUCCESS,
            'EXPIREE': AppColors.ERROR,
            'RESILIEE': AppColors.TEXT_SECONDARY,
            'RENOUVELEE': Colors.BLUE,
        }
        statut_color = statut_colors.get(statut, AppColors.TEXT_SECONDARY)
        
        # Informations détaillées
        details_content = Column(
            [
                # En-tête
                Row(
                    [
                        Icon(Icons.DESCRIPTION, size=32, color=AppColors.PRIMARY),
                        Column(
                            [
                                Text(
                                    reservation.get('numero_contrat', 'N/A'),
                                    size=18,
                                    weight=FontWeight.BOLD,
                                ),
                                Container(
                                    content=Text(
                                        statut_display,
                                        size=12,
                                        weight=FontWeight.BOLD,
                                        color=Colors.WHITE,
                                    ),
                                    bgcolor=statut_color,
                                    padding=ft.padding.symmetric(horizontal=12, vertical=4),
                                    border_radius=border_radius.all(15),
                                ),
                            ],
                            spacing=5,
                        ),
                    ],
                    spacing=15,
                ),
                
                Divider(height=20),
                
                # Informations de la concession
                Text("📋 Informations de la concession", size=14, weight=FontWeight.BOLD),
                self._detail_row("Type", reservation.get('type_concession', 'N/A').replace('_', ' ').title()),
                self._detail_row("Durée", f"{reservation.get('duree_annees', 'N/A')} an(s)" if reservation.get('duree_annees') else "Perpétuelle"),
                self._detail_row("Date de début", self._format_date(reservation.get('date_debut'))),
                self._detail_row("Date de fin", self._format_date(reservation.get('date_fin')) if reservation.get('date_fin') else "Perpétuelle"),
                self._detail_row("Date de signature", self._format_date(reservation.get('date_signature'))),
                
                Divider(height=15),
                
                # Informations du caveau
                Text("📍 Emplacement", size=14, weight=FontWeight.BOLD),
                self._detail_row("Caveau", reservation.get('caveau_code', 'N/A')),
                self._detail_row("Zone", reservation.get('zone_nom', 'N/A')),
                
                Divider(height=15),
                
                # Informations financières
                Text("💰 Informations financières", size=14, weight=FontWeight.BOLD),
                self._detail_row("Montant total", f"{reservation.get('montant_total', 0):,.2f} FC"),
                self._detail_row("Montant payé", f"{reservation.get('montant_paye', 0):,.2f} FC"),
                self._detail_row(
                    "Reste à payer",
                    f"{reservation.get('montant_total', 0) - reservation.get('montant_paye', 0):,.2f} FC"
                ),
                
                Divider(height=15),
                
                # Jours restants
                Text("⏰ Échéance", size=14, weight=FontWeight.BOLD),
                self._detail_row(
                    "Jours restants",
                    f"{reservation.get('jours_restants', 'N/A')} jour(s)" if reservation.get('jours_restants') is not None else "Perpétuelle"
                ),
            ],
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
        )
        
        dialog = ft.AlertDialog(
            title=Text("Détails de la réservation"),
            content=Container(
                content=details_content,
                width=500,
                height=500,
            ),
            actions=[
                ft.TextButton("Fermer", on_click=lambda _: self.page.close(dialog)),
            ],
        )
        
        self.page.open(dialog)
    
    def _detail_row(self, label: str, value: str) -> Row:
        """Crée une ligne de détail."""
        return Row(
            [
                Text(f"{label} :", size=13, color=AppColors.TEXT_SECONDARY, width=150),
                Text(value, size=13, weight=FontWeight.W_500),
            ],
            spacing=10,
        )
    
    def _load_reservations(self):
        """Charge les réservations depuis l'API."""
        self.loading.visible = True
        self.error_text.value = ""
        self.page.update()
        
        try:
            # Récupérer les concessions de l'utilisateur
            concessions = api_client.get_concessions()
            
            # Filtrer pour ne garder que celles de l'utilisateur connecté
            user_id = self.app_state.user.get('id') if self.app_state.user else None
            if user_id:
                self.reservations = [c for c in concessions if c.get('concessionnaire_id') == user_id]
            else:
                self.reservations = concessions
            
            # Construire le tableau
            if self.reservations:
                self.reservations_table.rows = [
                    self._build_reservation_row(res) for res in self.reservations
                ]
            else:
                self.reservations_table.rows = []
            
            self.page.update()
        
        except APIError as e:
            self.error_text.value = f"Erreur de chargement : {e.message}"
        except Exception as e:
            self.error_text.value = f"Erreur : {str(e)}"
        finally:
            self.loading.visible = False
            self.page.update()
    
    def did_mount(self):
        """Appelé quand la page est montée."""
        self._load_reservations()
    
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
            selected_index=2,
            destinations=[
                NavigationBarDestination(icon=Icons.DASHBOARD, label="Accueil"),
                NavigationBarDestination(icon=Icons.MAP, label="Carte"),
                NavigationBarDestination(icon=Icons.BOOKMARK, label="Réservations"),
                NavigationBarDestination(icon=Icons.RECEIPT, label="Factures"),
            ],
            on_change=handle_change,
            bgcolor=Colors.WHITE,
        )