"""
Page de gestion des factures.
Affiche les factures de l'utilisateur avec historique des paiements.
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
    TextField,
    DataTable,
    DataColumn,
    DataCell,
    DataRow,
    ElevatedButton,
    OutlinedButton,
    border_radius,
    alignment,
    padding,
)
from frontend.api_client import api_client, APIError
from frontend.theme import AppColors, AppSpacing


class FacturesPage:
    """Page de gestion des factures."""
    
    def __init__(self, page: ft.Page, app_state):
        self.page = page
        self.app_state = app_state
        
        # Données
        self.factures = []
        self.filtered_factures = []
        
        # Filtres
        self.statut_filter = Dropdown(
            label="Statut",
            width=180,
            border_radius=border_radius.all(10),
            options=[
                dropdown.Option(key="", text="Tous les statuts"),
                dropdown.Option(key="BROUILLON", text="⚫ Brouillon"),
                dropdown.Option(key="EMISE", text="🔵 Émise"),
                dropdown.Option(key="PARTIELLEMENT_PAYEE", text="🟠 Partiellement payée"),
                dropdown.Option(key="PAYEE", text="🟢 Payée"),
                dropdown.Option(key="ANNULEE", text="⚫ Annulée"),
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
        
        # Statistiques rapides
        self.total_factures_card = self._create_stat_card(
            "Total Factures", "0", Icons.RECEIPT, Colors.BLUE, "total"
        )
        self.factures_payees_card = self._create_stat_card(
            "Payées", "0", Icons.CHECK_CIRCLE, Colors.GREEN, "payees"
        )
        self.factures_en_retard_card = self._create_stat_card(
            "En Retard", "0", Icons.WARNING, Colors.RED, "retard"
        )
        self.montant_total_card = self._create_stat_card(
            "Montant Total", "0 FC", Icons.ACCOUNT_BALANCE, Colors.PURPLE, "montant"
        )
        
        # Tableau des factures
        self.factures_table = DataTable(
            columns=[
                DataColumn(Text("N° Facture")),
                DataColumn(Text("Date émission")),
                DataColumn(Text("Date échéance")),
                DataColumn(Text("Montant total")),
                DataColumn(Text("Montant payé")),
                DataColumn(Text("Reste")),
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
        
        # Compteurs
        self.count_text = Text("", size=13, color=AppColors.TEXT_SECONDARY)
        
        # Chargement
        self.loading = ft.ProgressRing(visible=True)
        self.error_text = Text("", color=Colors.RED_400, size=14)
    
    def _create_stat_card(self, title: str, value: str, icon: str, color: str, stat_key: str) -> Card:
        """Crée une carte de statistique."""
        return Card(
            content=Container(
                content=Column(
                    [
                        Icon(icon, size=32, color=color),
                        Text(value, size=22, weight=FontWeight.BOLD, key=f"value_{stat_key}"),
                        Text(title, size=12, color=AppColors.TEXT_SECONDARY),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8,
                ),
                padding=15,
                width=180,
                height=120,
                border_radius=border_radius.all(10),
            ),
            elevation=2,
        )
    
    def _update_stat_value(self, card: Card, stat_key: str, value: str):
        """Met à jour la valeur d'une carte de statistique."""
        try:
            for control in card.content.content.controls:
                if hasattr(control, 'key') and control.key == f"value_{stat_key}":
                    control.value = value
                    break
        except Exception:
            pass
    
    def build(self) -> View:
        """Construit la vue des factures."""
        
        return View(
            "/factures",
            [
                self._create_app_bar("Mes Factures"),
                Container(
                    content=Column(
                        [
                            # En-tête
                            Row(
                                [
                                    Column(
                                        [
                                            Text(
                                                "💳 Mes Factures",
                                                size=24,
                                                weight=FontWeight.BOLD,
                                                color=AppColors.TEXT_PRIMARY,
                                            ),
                                            Text(
                                                "Historique et suivi de vos factures",
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
                                                on_click=lambda _: self._load_factures(),
                                            ),
                                        ]
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            
                            Divider(height=20),
                            
                            # Statistiques rapides
                            Row(
                                [
                                    self.total_factures_card,
                                    self.factures_payees_card,
                                    self.factures_en_retard_card,
                                    self.montant_total_card,
                                ],
                                wrap=True,
                                spacing=15,
                                alignment=ft.MainAxisAlignment.CENTER,
                            ),
                            
                            Divider(height=20),
                            
                            # Barre de filtres
                            Container(
                                content=Row(
                                    [
                                        Icon(Icons.FILTER_LIST, color=AppColors.PRIMARY),
                                        Text("Filtres :", weight=FontWeight.BOLD, size=14),
                                        self.statut_filter,
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
                            
                            # Tableau des factures
                            Container(
                                content=self.factures_table,
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
    
    def _build_facture_row(self, facture: dict) -> DataRow:
        """Construit une ligne du tableau pour une facture."""
        statut = facture.get('statut', 'EMISE')
        statut_display = facture.get('statut_display', statut)
        
        # Couleur du statut
        statut_colors = {
            'BROUILLON': AppColors.TEXT_SECONDARY,
            'EMISE': Colors.BLUE,
            'PARTIELLEMENT_PAYEE': Colors.ORANGE,
            'PAYEE': AppColors.SUCCESS,
            'ANNULEE': AppColors.TEXT_SECONDARY,
        }
        statut_color = statut_colors.get(statut, AppColors.TEXT_SECONDARY)
        
        # Montants
        montant_total = facture.get('montant_total', 0)
        montant_paye = facture.get('montant_paye', 0)
        montant_restant = facture.get('montant_restant', 0)
        
        # Indicateur de retard
        est_en_retard = facture.get('est_en_retard', False)
        
        return DataRow(
            cells=[
                DataCell(
                    Text(
                        facture.get('numero_facture', 'N/A'),
                        weight=FontWeight.BOLD,
                        size=12,
                    )
                ),
                DataCell(
                    Text(
                        self._format_date(facture.get('date_emission')),
                        size=12,
                    )
                ),
                DataCell(
                    Row(
                        [
                            Text(
                                self._format_date(facture.get('date_echeance')),
                                size=12,
                                color=Colors.RED if est_en_retard else Colors.BLACK,
                            ),
                            Icon(Icons.WARNING, size=14, color=Colors.RED) if est_en_retard else None,
                        ],
                        spacing=5,
                    )
                ),
                DataCell(
                    Text(
                        f"{montant_total:,.0f} FC",
                        size=12,
                        weight=FontWeight.W_500,
                    )
                ),
                DataCell(
                    Text(
                        f"{montant_paye:,.0f} FC",
                        size=12,
                        color=AppColors.SUCCESS if montant_paye > 0 else AppColors.TEXT_SECONDARY,
                    )
                ),
                DataCell(
                    Text(
                        f"{montant_restant:,.0f} FC",
                        size=12,
                        weight=FontWeight.BOLD,
                        color=Colors.RED if montant_restant > 0 else AppColors.SUCCESS,
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
                    Row(
                        [
                            IconButton(
                                Icons.VISIBILITY,
                                icon_size=18,
                                tooltip="Voir les détails",
                                on_click=lambda _, f=facture: self._show_details(f),
                            ),
                            IconButton(
                                Icons.DOWNLOAD,
                                icon_size=18,
                                tooltip="Télécharger PDF",
                                on_click=lambda _, f=facture: self._download_pdf(f),
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
    
    def _show_details(self, facture: dict):
        """Affiche les détails d'une facture."""
        statut = facture.get('statut', 'EMISE')
        statut_display = facture.get('statut_display', statut)
        
        # Couleur du statut
        statut_colors = {
            'BROUILLON': AppColors.TEXT_SECONDARY,
            'EMISE': Colors.BLUE,
            'PARTIELLEMENT_PAYEE': Colors.ORANGE,
            'PAYEE': AppColors.SUCCESS,
            'ANNULEE': AppColors.TEXT_SECONDARY,
        }
        statut_color = statut_colors.get(statut, AppColors.TEXT_SECONDARY)
        
        # Montants
        montant_ht = facture.get('montant_ht', 0)
        montant_tva = facture.get('montant_tva', 0)
        montant_total = facture.get('montant_total', 0)
        montant_paye = facture.get('montant_paye', 0)
        montant_restant = facture.get('montant_restant', 0)
        
        # Informations détaillées
        details_content = Column(
            [
                # En-tête
                Row(
                    [
                        Icon(Icons.RECEIPT, size=32, color=AppColors.PRIMARY),
                        Column(
                            [
                                Text(
                                    facture.get('numero_facture', 'N/A'),
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
                
                # Dates
                Text("📅 Dates", size=14, weight=FontWeight.BOLD),
                self._detail_row("Date d'émission", self._format_date(facture.get('date_emission'))),
                self._detail_row("Date d'échéance", self._format_date(facture.get('date_echeance'))),
                
                Divider(height=15),
                
                # Informations financières
                Text("💰 Détails financiers", size=14, weight=FontWeight.BOLD),
                self._detail_row("Montant HT", f"{montant_ht:,.2f} FC"),
                self._detail_row("TVA", f"{facture.get('taux_tva', 0)}% ({montant_tva:,.2f} FC)"),
                self._detail_row("Montant total TTC", f"{montant_total:,.2f} FC"),
                
                Divider(height=10),
                
                self._detail_row("Montant payé", f"{montant_paye:,.2f} FC"),
                self._detail_row(
                    "Reste à payer",
                    f"{montant_restant:,.2f} FC",
                    highlight=montant_restant > 0
                ),
                
                Divider(height=15),
                
                # Concession associée
                Text("📋 Concession associée", size=14, weight=FontWeight.BOLD),
                self._detail_row("N° Contrat", facture.get('concession_numero', 'N/A')),
                self._detail_row("Caveau", facture.get('caveau_code', 'N/A')),
                
                Divider(height=15),
                
                # Boutons d'action
                Row(
                    [
                        ElevatedButton(
                            "📥 Télécharger PDF",
                            icon=Icons.DOWNLOAD,
                            bgcolor=AppColors.PRIMARY,
                            color=Colors.WHITE,
                            on_click=lambda _: self._download_pdf(facture),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
            ],
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
        )
        
        dialog = ft.AlertDialog(
            title=Text("Détails de la facture"),
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
    
    def _detail_row(self, label: str, value: str, highlight: bool = False) -> Row:
        """Crée une ligne de détail."""
        return Row(
            [
                Text(f"{label} :", size=13, color=AppColors.TEXT_SECONDARY, width=150),
                Text(
                    value,
                    size=13,
                    weight=FontWeight.BOLD if highlight else FontWeight.W_500,
                    color=Colors.RED if highlight else AppColors.TEXT_PRIMARY,
                ),
            ],
            spacing=10,
        )
    
    def _download_pdf(self, facture: dict):
        """Télécharge le PDF de la facture."""
        self.page.open(
            ft.AlertDialog(
                title=Text("Téléchargement PDF"),
                content=Text(f"Le PDF de la facture {facture.get('numero_facture')} sera téléchargé.\n\nFonctionnalité à implémenter avec le backend."),
                actions=[
                    ft.TextButton("OK", on_click=lambda _: self.page.close(self.page.overlay[-1]))
                ],
            )
        )
    
    def _on_filter_changed(self, e):
        """Applique les filtres sur la liste des factures."""
        statut = self.statut_filter.value or ""
        search = (self.search_field.value or "").lower()
        
        filtered = self.factures
        
        if statut:
            filtered = [f for f in filtered if f.get('statut') == statut]
        
        if search:
            filtered = [
                f for f in filtered
                if search in f.get('numero_facture', '').lower()
            ]
        
        self.filtered_factures = filtered
        self._render_table()
    
    def _reset_filters(self, e):
        """Réinitialise tous les filtres."""
        self.statut_filter.value = ""
        self.search_field.value = ""
        self.filtered_factures = self.factures
        self._render_table()
        self.page.update()
    
    def _render_table(self):
        """Rendu du tableau des factures."""
        self.factures_table.rows = [
            self._build_facture_row(facture) for facture in self.filtered_factures
        ]
        
        # Compteurs
        total = len(self.filtered_factures)
        payees = sum(1 for f in self.filtered_factures if f.get('statut') == 'PAYEE')
        self.count_text.value = f"Affichage : {total} facture(s) dont {payees} payée(s)"
        
        self.page.update()
    
    def _update_stats(self):
        """Met à jour les statistiques."""
        total = len(self.factures)
        payees = sum(1 for f in self.factures if f.get('statut') == 'PAYEE')
        en_retard = sum(1 for f in self.factures if f.get('est_en_retard', False))
        montant_total = sum(f.get('montant_total', 0) for f in self.factures)
        
        self._update_stat_value(self.total_factures_card, "total", str(total))
        self._update_stat_value(self.factures_payees_card, "payees", str(payees))
        self._update_stat_value(self.factures_en_retard_card, "retard", str(en_retard))
        self._update_stat_value(self.montant_total_card, "montant", f"{montant_total:,.0f} FC")
    
    def _load_factures(self):
        """Charge les factures depuis l'API."""
        self.loading.visible = True
        self.error_text.value = ""
        self.page.update()
        
        try:
            # Récupérer les factures de l'utilisateur
            self.factures = api_client.get_factures()
            self.filtered_factures = self.factures
            
            # Mettre à jour les statistiques
            self._update_stats()
            
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
        self._load_factures()
    
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
            selected_index=3,
            destinations=[
                NavigationBarDestination(icon=Icons.DASHBOARD, label="Accueil"),
                NavigationBarDestination(icon=Icons.MAP, label="Carte"),
                NavigationBarDestination(icon=Icons.BOOKMARK, label="Réservations"),
                NavigationBarDestination(icon=Icons.RECEIPT, label="Factures"),
            ],
            on_change=handle_change,
            bgcolor=Colors.WHITE,
        )