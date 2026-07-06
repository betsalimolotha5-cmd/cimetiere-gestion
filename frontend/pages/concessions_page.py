"""
Page de gestion des concessions (Admin/Secrétariat).
Affiche toutes les concessions avec filtres et actions de validation.
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
    PopupMenuButton,
    PopupMenuItem,
    Dropdown,
    dropdown,
    TextField,
    DataTable,
    DataColumn,
    DataCell,
    DataRow,
    ElevatedButton,
    border_radius,
    alignment,
    padding,
)
from frontend.api_client import api_client, APIError
from frontend.theme import AppColors, AppSpacing


class ConcessionsPage:
    """Page de gestion des concessions."""
    
    def __init__(self, page: ft.Page, app_state):
        self.page = page
        self.app_state = app_state
        
        # Données
        self.concessions = []
        self.filtered_concessions = []
        
        # Filtres
        self.statut_filter = Dropdown(
            label="Statut",
            width=180,
            border_radius=border_radius.all(10),
            options=[
                dropdown.Option(key="", text="Tous les statuts"),
                dropdown.Option(key="ACTIVE", text="🟢 Active"),
                dropdown.Option(key="EXPIREE", text="🔴 Expirée"),
                dropdown.Option(key="RESILIEE", text="⚫ Résiliée"),
                dropdown.Option(key="RENOUVELEE", text="🔵 Renouvelée"),
            ],
            on_change=self._on_filter_changed,
        )
        
        self.type_filter = Dropdown(
            label="Type",
            width=180,
            border_radius=border_radius.all(10),
            options=[
                dropdown.Option(key="", text="Tous les types"),
                dropdown.Option(key="TEMPORAIRE", text="Temporaire"),
                dropdown.Option(key="PERPETUELLE", text="Perpétuelle"),
            ],
            on_change=self._on_filter_changed,
        )
        
        self.search_field = TextField(
            label="Rechercher...",
            prefix_icon=Icons.SEARCH,
            width=250,
            border_radius=border_radius.all(10),
            on_change=self._on_filter_changed,
        )
        
        # Tableau des concessions
        self.concessions_table = DataTable(
            columns=[
                DataColumn(Text("N° Contrat")),
                DataColumn(Text("Concessionnaire")),
                DataColumn(Text("Caveau")),
                DataColumn(Text("Type")),
                DataColumn(Text("Date début")),
                DataColumn(Text("Date fin")),
                DataColumn(Text("Statut")),
                DataColumn(Text("Montant")),
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
        
        # Compteurs
        self.count_text = Text("", size=13, color=AppColors.TEXT_SECONDARY)
        
        # Chargement
        self.loading = ft.ProgressRing(visible=True)
        self.error_text = Text("", color=Colors.RED_400, size=14)
    
    def build(self) -> View:
        """Construit la vue des concessions."""
        
        return View(
            "/concessions",
            [
                self._create_app_bar("Gestion des Concessions"),
                Container(
                    content=Column(
                        [
                            # En-tête
                            Row(
                                [
                                    Column(
                                        [
                                            Text(
                                                "📋 Gestion des Concessions",
                                                size=24,
                                                weight=FontWeight.BOLD,
                                                color=AppColors.TEXT_PRIMARY,
                                            ),
                                            Text(
                                                "Administration et suivi de toutes les concessions",
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
                                                on_click=lambda _: self._load_concessions(),
                                            ),
                                        ]
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
                                        self.statut_filter,
                                        self.type_filter,
                                        self.search_field,
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
                            
                            # Tableau des concessions
                            Container(
                                content=self.concessions_table,
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
            ],
        )
    
    def _build_concession_row(self, concession: dict) -> DataRow:
        """Construit une ligne du tableau pour une concession."""
        statut = concession.get('statut', 'ACTIVE')
        statut_display = concession.get('statut_display', statut)
        
        # Couleur du statut
        statut_colors = {
            'ACTIVE': AppColors.SUCCESS,
            'EXPIREE': AppColors.ERROR,
            'RESILIEE': AppColors.TEXT_SECONDARY,
            'RENOUVELEE': Colors.BLUE,
        }
        statut_color = statut_colors.get(statut, AppColors.TEXT_SECONDARY)
        
        # Date de fin
        date_fin = concession.get('date_fin')
        date_fin_text = self._format_date(date_fin) if date_fin else "Perpétuelle"
        
        # Jours restants
        jours_restants = concession.get('jours_restants')
        if jours_restants is not None and jours_restants > 0:
            date_fin_text += f"\n({jours_restants}j)"
        
        # Concessionnaire
        concessionnaire_nom = concession.get('concessionnaire_email', 'N/A')
        
        return DataRow(
            cells=[
                DataCell(
                    Text(
                        concession.get('numero_contrat', 'N/A'),
                        weight=FontWeight.BOLD,
                        size=12,
                    )
                ),
                DataCell(
                    Text(
                        concessionnaire_nom,
                        size=12,
                    )
                ),
                DataCell(
                    Text(
                        concession.get('caveau_code', 'N/A'),
                        size=12,
                    )
                ),
                DataCell(
                    Text(
                        concession.get('type_concession', 'N/A').replace('_', ' ').title(),
                        size=12,
                    )
                ),
                DataCell(
                    Text(
                        self._format_date(concession.get('date_debut')),
                        size=12,
                    )
                ),
                DataCell(
                    Text(
                        date_fin_text,
                        size=11,
                    )
                ),
                DataCell(
                    Container(
                        content=Text(
                            statut_display,
                            size=10,
                            weight=FontWeight.BOLD,
                            color=Colors.WHITE,
                        ),
                        bgcolor=statut_color,
                        padding=ft.padding.symmetric(horizontal=10, vertical=4),
                        border_radius=border_radius.all(15),
                    )
                ),
                DataCell(
                    Text(
                        f"{concession.get('montant_total', 0):,.0f} FC",
                        size=12,
                        weight=FontWeight.W_500,
                    )
                ),
                DataCell(
                    Row(
                        [
                            IconButton(
                                Icons.VISIBILITY,
                                icon_size=18,
                                tooltip="Voir les détails",
                                on_click=lambda _, c=concession: self._show_details(c),
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
    
    def _show_details(self, concession: dict):
        """Affiche les détails d'une concession."""
        statut = concession.get('statut', 'ACTIVE')
        statut_display = concession.get('statut_display', statut)
        
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
                                    concession.get('numero_contrat', 'N/A'),
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
                
                # Concessionnaire
                Text("👤 Concessionnaire", size=14, weight=FontWeight.BOLD),
                self._detail_row("Email", concession.get('concessionnaire_email', 'N/A')),
                self._detail_row("ID", str(concession.get('concessionnaire_id', 'N/A'))),
                
                Divider(height=15),
                
                # Informations de la concession
                Text("📋 Informations de la concession", size=14, weight=FontWeight.BOLD),
                self._detail_row("Type", concession.get('type_concession', 'N/A').replace('_', ' ').title()),
                self._detail_row("Durée", f"{concession.get('duree_annees', 'N/A')} an(s)" if concession.get('duree_annees') else "Perpétuelle"),
                self._detail_row("Date de début", self._format_date(concession.get('date_debut'))),
                self._detail_row("Date de fin", self._format_date(concession.get('date_fin')) if concession.get('date_fin') else "Perpétuelle"),
                self._detail_row("Date de signature", self._format_date(concession.get('date_signature'))),
                
                Divider(height=15),
                
                # Informations du caveau
                Text("📍 Emplacement", size=14, weight=FontWeight.BOLD),
                self._detail_row("Caveau", concession.get('caveau_code', 'N/A')),
                
                Divider(height=15),
                
                # Informations financières
                Text("💰 Informations financières", size=14, weight=FontWeight.BOLD),
                self._detail_row("Montant total", f"{concession.get('montant_total', 0):,.2f} FC"),
                self._detail_row("Montant payé", f"{concession.get('montant_paye', 0):,.2f} FC"),
                self._detail_row(
                    "Reste à payer",
                    f"{concession.get('montant_total', 0) - concession.get('montant_paye', 0):,.2f} FC"
                ),
                
                Divider(height=15),
                
                # Échéance
                Text("⏰ Échéance", size=14, weight=FontWeight.BOLD),
                self._detail_row(
                    "Jours restants",
                    f"{concession.get('jours_restants', 'N/A')} jour(s)" if concession.get('jours_restants') is not None else "Perpétuelle"
                ),
            ],
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
        )
        
        dialog = ft.AlertDialog(
            title=Text("Détails de la concession"),
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
    
    def _on_filter_changed(self, e):
        """Applique les filtres sur la liste des concessions."""
        statut = self.statut_filter.value or ""
        type_concession = self.type_filter.value or ""
        search = (self.search_field.value or "").lower()
        
        filtered = self.concessions
        
        if statut:
            filtered = [c for c in filtered if c.get('statut') == statut]
        
        if type_concession:
            filtered = [c for c in filtered if c.get('type_concession') == type_concession]
        
        if search:
            filtered = [
                c for c in filtered
                if search in c.get('numero_contrat', '').lower() or
                   search in c.get('concessionnaire_email', '').lower() or
                   search in c.get('caveau_code', '').lower()
            ]
        
        self.filtered_concessions = filtered
        self._render_table()
    
    def _reset_filters(self, e):
        """Réinitialise tous les filtres."""
        self.statut_filter.value = ""
        self.type_filter.value = ""
        self.search_field.value = ""
        self.filtered_concessions = self.concessions
        self._render_table()
        self.page.update()
    
    def _render_table(self):
        """Rendu du tableau des concessions."""
        self.concessions_table.rows = [
            self._build_concession_row(concession) for concession in self.filtered_concessions
        ]
        
        # Compteurs
        total = len(self.filtered_concessions)
        actives = sum(1 for c in self.filtered_concessions if c.get('statut') == 'ACTIVE')
        self.count_text.value = f"Affichage : {total} concession(s) dont {actives} active(s)"
        
        self.page.update()
    
    def _load_concessions(self):
        """Charge les concessions depuis l'API."""
        self.loading.visible = True
        self.error_text.value = ""
        self.page.update()
        
        try:
            # Récupérer toutes les concessions
            self.concessions = api_client.get_concessions()
            self.filtered_concessions = self.concessions
            
            # Construire le tableau
            self._render_table()
        
        except APIError as e:
            self.error_text.value = f"Erreur de chargement : {e.message}"
        except Exception as e:
            self.error_text.value = f"Erreur : {str(e)}"
        finally:
            self.loading.visible = False
            self.page.update()
    
    def did_mount(self):
        """Appelé quand la page est montée."""
        self._load_concessions()
    
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