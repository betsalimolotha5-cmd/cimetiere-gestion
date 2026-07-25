"""
Page Admin Dashboard - Tableau de bord principal pour l'administration.
Cette page remplace le bouton "Administration" du dashboard.
"""
import flet as ft
from flet import (
    View, AppBar, Container, Column, Row, Text, Icon, Icons, Colors,
    FontWeight, TextAlign, Card, ElevatedButton, IconButton, 
    NavigationBar, NavigationBarDestination, border_radius, alignment, padding,
    DataTable, DataColumn, DataRow, DataCell, PopupMenuButton, PopupMenuItem,
    Divider, Tabs, Tab, TextField, Dropdown, FilledButton, OutlinedButton,
    AlertDialog, SnackBar, Chip, Badge
)
from frontend.api_client import api_client, APIError
from frontend.theme import AppColors, AppSpacing


class AdminDashboardPage:
    """Page principale du tableau de bord admin."""
    
    def __init__(self, page: ft.Page, app_state):
        self.page = page
        self.app_state = app_state
        self.selected_tab = 0
        
        # Données pour les statistiques
        self.stats_data = {}
        
        # États des tables
        self.users_data = []
        self.reservations_data = []
        self.factures_data = []
        self.paiements_data = []
        
        # Filtres
        self.filter_statut_user = ft.Dropdown(
            label="Filtrer par statut",
            options=[
                ft.dropdown.Option("Tous"),
                ft.dropdown.Option("Actif"),
                ft.dropdown.Option("Inactif"),
            ],
            value="Tous",
            width=200,
        )
        
        self.filter_statut_reservation = ft.Dropdown(
            label="Filtrer par statut",
            options=[
                ft.dropdown.Option("Tous"),
                ft.dropdown.Option("En attente"),
                ft.dropdown.Option("Validée"),
                ft.dropdown.Option("Refusée"),
            ],
            value="Tous",
            width=200,
        )
        
        self.filter_statut_facture = ft.Dropdown(
            label="Filtrer par statut",
            options=[
                ft.dropdown.Option("Tous"),
                ft.dropdown.Option("Brouillon"),
                ft.dropdown.Option("Émise"),
                ft.dropdown.Option("Partiellement payée"),
                ft.dropdown.Option("Payée"),
                ft.dropdown.Option("Annulée"),
            ],
            value="Tous",
            width=200,
        )
        
        # Indicateur de chargement
        self.loading = ft.ProgressRing(visible=False)
        self.error_text = Text("", color=Colors.RED_400, size=14)
        
        # Snackbar pour les notifications
        self.snackbar = SnackBar(
            content=Text(""),
            open=False,
            duration=3000,
        )
    
    def build(self) -> View:
        """Construit la vue du tableau de bord admin."""
        
        # Vérifier que l'utilisateur est admin
        user = self.app_state.user or {}
        user_role = user.get('role', 'CLIENT')
        
        if user_role != 'ADMIN':
            return View(
                "/admin",
                [
                    AppBar(title=Text("Accès refusé"), bgcolor=AppColors.PRIMARY),
                    Container(
                        content=Column(
                            [
                                Icon(Icons.LOCK, size=80, color=Colors.RED_500),
                                Text("Accès réservé aux administrateurs", 
                                     size=20, weight=FontWeight.BOLD, color=Colors.RED_500),
                                Text("Vous n'avez pas les permissions nécessaires.", 
                                     size=14, color=Colors.GREY_600),
                                ElevatedButton(
                                    "Retour au dashboard",
                                    on_click=lambda _: self.page.go("/dashboard"),
                                    icon=Icons.ARROW_BACK,
                                )
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=20,
                        ),
                        alignment=alignment.center,
                        expand=True,
                        padding=40,
                    ),
                ],
            )
        
        # Créer les onglets
        tabs = [
            Tab(text="📊 Tableau de bord", icon=Icons.DASHBOARD),
            Tab(text="👥 Utilisateurs", icon=Icons.PEOPLE),
            Tab(text="📋 Réservations", icon=Icons.BOOKMARK),
            Tab(text="💰 Factures", icon=Icons.RECEIPT),
            Tab(text="💳 Paiements", icon=Icons.PAYMENTS),
        ]
        
        return View(
            "/admin",
            [
                self._create_app_bar(),
                Container(
                    content=Column(
                        [
                            # Onglets
                            Tabs(
                                tabs=tabs,
                                selected_index=self.selected_tab,
                                on_change=self._on_tab_change,
                                height=50,
                            ),
                            
                            # Contenu dynamique
                            Container(
                                content=self._get_tab_content(self.selected_tab),
                                expand=True,
                                padding=20,
                            ),
                            
                            # Snackbar
                            self.snackbar,
                        ],
                        spacing=0,
                    ),
                    expand=True,
                    bgcolor=AppColors.BACKGROUND,
                    padding=10,
                ),
                self._create_navigation_bar(),
            ],
        )
    
    def _create_app_bar(self) -> AppBar:
        """Crée la barre d'application."""
        user = self.app_state.user or {}
        first_letter = (user.get('first_name') or 'A')[0].upper()
        
        return AppBar(
            title=Text("Admin Dashboard"),
            center_title=True,
            bgcolor=AppColors.PRIMARY,
            color=Colors.WHITE,
            actions=[
                IconButton(
                    Icons.REFRESH,
                    tooltip="Actualiser",
                    on_click=self._load_all_data,
                ),
                PopupMenuButton(
                    items=[
                        PopupMenuItem(
                            text="Tableau de bord",
                            icon=Icons.DASHBOARD,
                            on_click=lambda _: self._navigate_to_tab(0),
                        ),
                        PopupMenuItem(
                            text="Utilisateurs",
                            icon=Icons.PEOPLE,
                            on_click=lambda _: self._navigate_to_tab(1),
                        ),
                        PopupMenuItem(
                            text="Réservations",
                            icon=Icons.BOOKMARK,
                            on_click=lambda _: self._navigate_to_tab(2),
                        ),
                        PopupMenuItem(
                            text="Factures",
                            icon=Icons.RECEIPT,
                            on_click=lambda _: self._navigate_to_tab(3),
                        ),
                        PopupMenuItem(
                            text="Paiements",
                            icon=Icons.PAYMENTS,
                            on_click=lambda _: self._navigate_to_tab(4),
                        ),
                        PopupMenuItem(),
                        PopupMenuItem(
                            text="Retour au Dashboard",
                            icon=Icons.ARROW_BACK,
                            on_click=lambda _: self.page.go("/dashboard"),
                        ),
                    ],
                ),
            ],
        )
    
    def _create_navigation_bar(self) -> NavigationBar:
        """Crée la barre de navigation inférieure."""
        return NavigationBar(
            destinations=[
                NavigationBarDestination(icon=Icons.DASHBOARD, label="Accueil"),
                NavigationBarDestination(icon=Icons.MAP, label="Carte"),
                NavigationBarDestination(icon=Icons.BOOKMARK, label="Réservations"),
                NavigationBarDestination(icon=Icons.RECEIPT, label="Factures"),
            ],
            bgcolor=Colors.WHITE,
        )
    
    def _on_tab_change(self, e):
        """Gère le changement d'onglet."""
        self.selected_tab = e.control.selected_index
        self._load_tab_data(self.selected_tab)
        self.page.update()
    
    def _navigate_to_tab(self, tab_index):
        """Navigue vers un onglet spécifique."""
        self.selected_tab = tab_index
        self._load_tab_data(tab_index)
        self.page.update()
    
    def _get_tab_content(self, tab_index: int):
        """Retourne le contenu pour l'onglet sélectionné."""
        if tab_index == 0:
            return self._build_dashboard_tab()
        elif tab_index == 1:
            return self._build_users_tab()
        elif tab_index == 2:
            return self._build_reservations_tab()
        elif tab_index == 3:
            return self._build_factures_tab()
        elif tab_index == 4:
            return self._build_paiements_tab()
        else:
            return Text("Contenu non disponible")
    
    def _build_dashboard_tab(self):
        """Construit l'onglet Tableau de bord."""
        return Column(
            [
                Text("📊 Tableau de bord Administratif", size=24, weight=FontWeight.BOLD),
                Text("Vue d'ensemble de votre cimetière", size=14, color=AppColors.TEXT_SECONDARY),
                
                Divider(height=30),
                
                # Statistiques principales
                Row(
                    [
                        self._create_stat_card("👥 Utilisateurs", str(self.stats_data.get('total_users', 0)), Icons.PEOPLE, Colors.BLUE),
                        self._create_stat_card("📋 Réservations", str(self.stats_data.get('reservations_en_attente', 0)), Icons.BOOKMARK, Colors.ORANGE),
                        self._create_stat_card("💰 Factures", str(self.stats_data.get('factures_impayees', 0)), Icons.RECEIPT, Colors.RED),
                        self._create_stat_card("💳 Paiements", str(self.stats_data.get('paiements_en_attente', 0)), Icons.PAYMENTS, Colors.GREEN),
                    ],
                    wrap=True,
                    spacing=20,
                ),
                
                Divider(height=30),
                
                # Statistiques cimetière
                Text("🏛️ Statistiques du Cimetière", size=20, weight=FontWeight.BOLD),
                
                Row(
                    [
                        self._create_stat_card("Total Caveaux", str(self.stats_data.get('total_caveaux', 0)), Icons.LOCATION_CITY, Colors.PURPLE),
                        self._create_stat_card("Disponibles", str(self.stats_data.get('caveaux_disponibles', 0)), Icons.CHECK_CIRCLE, Colors.GREEN),
                        self._create_stat_card("Occupés", str(self.stats_data.get('caveaux_occupes', 0)), Icons.BUSY, Colors.RED),
                        self._create_stat_card("Réservés", str(self.stats_data.get('caveaux_reserves', 0)), Icons.BOOKMARK, Colors.ORANGE),
                    ],
                    wrap=True,
                    spacing=20,
                ),
                
                Divider(height=30),
                
                # Statistiques financières
                Text("💰 Statistiques Financières", size=20, weight=FontWeight.BOLD),
                
                Row(
                    [
                        self._create_stat_card("Revenus du Mois", f"{self.stats_data.get('revenus_mois', 0):,.0f} FC", Icons.TRENDING_UP, Colors.TEAL),
                        self._create_stat_card("Revenus de l'Année", f"{self.stats_data.get('revenus_annee', 0):,.0f} FC", Icons.ACCOUNT_BALANCE, Colors.INDIGO),
                        self._create_stat_card("Taux de Recouvrement", f"{self.stats_data.get('taux_recouvrement', 0):.1f}%", Icons.PIE_CHART, Colors.CYAN),
                        self._create_stat_card("Factures en Retard", str(self.stats_data.get('factures_en_retard', 0)), Icons.WARNING, Colors.AMBER),
                    ],
                    wrap=True,
                    spacing=20,
                ),
                
                # Actions rapides
                Divider(height=30),
                Text("⚡ Actions Rapides", size=20, weight=FontWeight.BOLD),
                Row(
                    [
                        ElevatedButton(
                            "👤 Ajouter Utilisateur",
                            icon=Icons.PERSON_ADD,
                            on_click=self._show_add_user_dialog,
                            bgcolor=AppColors.PRIMARY,
                            color=Colors.WHITE,
                        ),
                        ElevatedButton(
                            "📊 Actualiser",
                            icon=Icons.REFRESH,
                            on_click=self._load_all_data,
                            bgcolor=Colors.GREY_600,
                            color=Colors.WHITE,
                        ),
                    ],
                    spacing=15,
                ),
                
                self.loading,
                self.error_text,
            ],
            spacing=20,
        )
    
    def _build_users_tab(self):
        """Construit l'onglet Utilisateurs."""
        return Column(
            [
                Row(
                    [
                        Text("👥 Gestion des Utilisateurs", size=24, weight=FontWeight.BOLD),
                        ft.Spacer(),
                        self.filter_statut_user,
                        ElevatedButton(
                            "🔍 Filtrer",
                            on_click=self._filter_users,
                            icon=Icons.FILTER_LIST,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                
                Divider(height=20),
                
                # Tableau des utilisateurs
                Container(
                    content=self._create_users_table(),
                    expand=True,
                ),
                
                self.loading,
                self.error_text,
            ],
            spacing=15,
        )
    
    def _build_reservations_tab(self):
        """Construit l'onglet Réservations."""
        return Column(
            [
                Row(
                    [
                        Text("📋 Gestion des Réservations", size=24, weight=FontWeight.BOLD),
                        ft.Spacer(),
                        self.filter_statut_reservation,
                        ElevatedButton(
                            "🔍 Filtrer",
                            on_click=self._filter_reservations,
                            icon=Icons.FILTER_LIST,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                
                Divider(height=20),
                
                # Tableau des réservations
                Container(
                    content=self._create_reservations_table(),
                    expand=True,
                ),
                
                self.loading,
                self.error_text,
            ],
            spacing=15,
        )
    
    def _build_factures_tab(self):
        """Construit l'onglet Factures."""
        return Column(
            [
                Row(
                    [
                        Text("💰 Gestion des Factures", size=24, weight=FontWeight.BOLD),
                        ft.Spacer(),
                        self.filter_statut_facture,
                        ElevatedButton(
                            "🔍 Filtrer",
                            on_click=self._filter_factures,
                            icon=Icons.FILTER_LIST,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                
                Divider(height=20),
                
                # Tableau des factures
                Container(
                    content=self._create_factures_table(),
                    expand=True,
                ),
                
                self.loading,
                self.error_text,
            ],
            spacing=15,
        )
    
    def _build_paiements_tab(self):
        """Construit l'onglet Paiements."""
        return Column(
            [
                Text("💳 Gestion des Paiements", size=24, weight=FontWeight.BOLD),
                
                Divider(height=20),
                
                # Tableau des paiements
                Container(
                    content=self._create_paiements_table(),
                    expand=True,
                ),
                
                self.loading,
                self.error_text,
            ],
            spacing=15,
        )
    
    def _create_stat_card(self, title: str, value: str, icon: str, color: str):
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
                width=220,
                height=140,
                border_radius=border_radius.all(12),
            ),
            elevation=3,
        )
    
    def _create_users_table(self):
        """Crée le tableau des utilisateurs."""
        rows = []
        for user in self.users_data:
            rows.append(
                DataRow(
                    cells=[
                        DataCell(Text(str(user.get('id', '')))),
                        DataCell(Text(user.get('email', ''))),
                        DataCell(Text(f"{user.get('first_name', '')} {user.get('last_name', '')}")),
                        DataCell(Chip(
                            label=Text(user.get('role', '')),
                            bgcolor=AppColors.PRIMARY,
                            color=Colors.WHITE,
                        )),
                        DataCell(Chip(
                            label=Text("Actif" if user.get('is_active', False) else "Inactif"),
                            bgcolor=Colors.GREEN if user.get('is_active', False) else Colors.RED,
                            color=Colors.WHITE,
                        )),
                        DataCell(Row(
                            [
                                IconButton(
                                    Icons.EDIT,
                                    tooltip="Modifier",
                                    on_click=lambda e, uid=user.get('id'): self._show_edit_user_dialog(uid),
                                    icon_size=18,
                                ),
                                IconButton(
                                    Icons.DELETE,
                                    tooltip="Supprimer",
                                    on_click=lambda e, uid=user.get('id'): self._confirm_delete_user(uid),
                                    icon_size=18,
                                    icon_color=Colors.RED_500,
                                ),
                            ],
                            spacing=5,
                        )),
                    ],
                )
            )
        
        return DataTable(
            columns=[
                DataColumn(label=Text("ID", weight=FontWeight.BOLD)),
                DataColumn(label=Text("Email", weight=FontWeight.BOLD)),
                DataColumn(label=Text("Nom", weight=FontWeight.BOLD)),
                DataColumn(label=Text("Rôle", weight=FontWeight.BOLD)),
                DataColumn(label=Text("Statut", weight=FontWeight.BOLD)),
                DataColumn(label=Text("Actions", weight=FontWeight.BOLD)),
            ],
            rows=rows,
            expand=True,
        )
    
    def _create_reservations_table(self):
        """Crée le tableau des réservations."""
        rows = []
        for reservation in self.reservations_data:
            statut_color = Colors.ORANGE if reservation.get('statut') == 'EN_ATTENTE' else (
                Colors.GREEN if reservation.get('statut') == 'VALIDEE' else Colors.RED
            )
            
            rows.append(
                DataRow(
                    cells=[
                        DataCell(Text(str(reservation.get('id', '')))),
                        DataCell(Text(reservation.get('caveau_code', ''))),
                        DataCell(Text(reservation.get('defunt_nom', '') + " " + reservation.get('defunt_prenom', ''))),
                        DataCell(Text(reservation.get('client_email', ''))),
                        DataCell(Chip(
                            label=Text(reservation.get('statut_display', reservation.get('statut', ''))),
                            bgcolor=statut_color,
                            color=Colors.WHITE,
                        )),
                        DataCell(Text(reservation.get('date_demande', '')[:10] if reservation.get('date_demande') else '')),
                        DataCell(Row(
                            [
                                ElevatedButton(
                                    "✅ Valider",
                                    on_click=lambda e, rid=reservation.get('id'): self._confirm_valider_reservation(rid),
                                    bgcolor=Colors.GREEN,
                                    color=Colors.WHITE,
                                    size=12,
                                    height=30,
                                ) if reservation.get('statut') == 'EN_ATTENTE' else Text(""),
                                ElevatedButton(
                                    "❌ Refuser",
                                    on_click=lambda e, rid=reservation.get('id'): self._show_refuser_reservation_dialog(rid),
                                    bgcolor=Colors.RED,
                                    color=Colors.WHITE,
                                    size=12,
                                    height=30,
                                ) if reservation.get('statut') == 'EN_ATTENTE' else Text(""),
                            ],
                            spacing=5,
                        )),
                    ],
                )
            )
        
        return DataTable(
            columns=[
                DataColumn(label=Text("ID", weight=FontWeight.BOLD)),
                DataColumn(label=Text("Caveau", weight=FontWeight.BOLD)),
                DataColumn(label=Text("Défunts", weight=FontWeight.BOLD)),
                DataColumn(label=Text("Client", weight=FontWeight.BOLD)),
                DataColumn(label=Text("Statut", weight=FontWeight.BOLD)),
                DataColumn(label=Text("Date", weight=FontWeight.BOLD)),
                DataColumn(label=Text("Actions", weight=FontWeight.BOLD)),
            ],
            rows=rows,
            expand=True,
        )
    
    def _create_factures_table(self):
        """Crée le tableau des factures."""
        rows = []
        for facture in self.factures_data:
            statut_color = {
                'BROUILLON': Colors.GREY,
                'EMISE': Colors.ORANGE,
                'PARTIELLEMENT_PAYEE': Colors.BLUE,
                'PAYEE': Colors.GREEN,
                'ANNULEE': Colors.RED,
            }.get(facture.get('statut'), Colors.BLACK)
            
            rows.append(
                DataRow(
                    cells=[
                        DataCell(Text(facture.get('numero_facture', ''))),
                        DataCell(Text(facture.get('client_email', ''))),
                        DataCell(Text(f"{facture.get('montant_total', 0):,.0f} FC")),
                        DataCell(Chip(
                            label=Text(facture.get('statut_display', facture.get('statut', ''))),
                            bgcolor=statut_color,
                            color=Colors.WHITE,
                        )),
                        DataCell(Text(facture.get('date_emission', '')[:10] if facture.get('date_emission') else '')),
                        DataCell(Row(
                            [
                                IconButton(
                                    Icons.PREVIEW,
                                    tooltip="Voir PDF",
                                    on_click=lambda e, fid=facture.get('id'): self._view_facture_pdf(fid),
                                    icon_size=18,
                                ),
                                IconButton(
                                    Icons.CHECK,
                                    tooltip="Marquer comme payée",
                                    on_click=lambda e, fid=facture.get('id'): self._confirm_marquer_payee(fid),
                                    icon_size=18,
                                    icon_color=Colors.GREEN,
                                ) if facture.get('statut') != 'PAYEE' else IconButton(Icons.CHECK, icon_size=18, disabled=True),
                            ],
                            spacing=5,
                        )),
                    ],
                )
            )
        
        return DataTable(
            columns=[
                DataColumn(label=Text("N° Facture", weight=FontWeight.BOLD)),
                DataColumn(label=Text("Client", weight=FontWeight.BOLD)),
                DataColumn(label=Text("Montant", weight=FontWeight.BOLD)),
                DataColumn(label=Text("Statut", weight=FontWeight.BOLD)),
                DataColumn(label=Text("Date", weight=FontWeight.BOLD)),
                DataColumn(label=Text("Actions", weight=FontWeight.BOLD)),
            ],
            rows=rows,
            expand=True,
        )
    
    def _create_paiements_table(self):
        """Crée le tableau des paiements."""
        rows = []
        for paiement in self.paiements_data:
            statut_color = {
                'EN_ATTENTE': Colors.ORANGE,
                'VALIDE': Colors.GREEN,
                'REFUSE': Colors.RED,
                'REMBOURSE': Colors.GREY,
            }.get(paiement.get('statut'), Colors.BLACK)
            
            rows.append(
                DataRow(
                    cells=[
                        DataCell(Text(paiement.get('numero_transaction', ''))),
                        DataCell(Text(paiement.get('facture_numero', ''))),
                        DataCell(Text(paiement.get('client_email', ''))),
                        DataCell(Text(f"{paiement.get('montant', 0):,.0f} FC")),
                        DataCell(Chip(
                            label=Text(paiement.get('statut_display', paiement.get('statut', ''))),
                            bgcolor=statut_color,
                            color=Colors.WHITE,
                        )),
                        DataCell(Row(
                            [
                                ElevatedButton(
                                    "✅ Valider",
                                    on_click=lambda e, pid=paiement.get('id'): self._confirm_valider_paiement(pid),
                                    bgcolor=Colors.GREEN,
                                    color=Colors.WHITE,
                                    size=12,
                                    height=30,
                                ) if paiement.get('statut') == 'EN_ATTENTE' else Text(""),
                                ElevatedButton(
                                    "❌ Refuser",
                                    on_click=lambda e, pid=paiement.get('id'): self._show_refuser_paiement_dialog(pid),
                                    bgcolor=Colors.RED,
                                    color=Colors.WHITE,
                                    size=12,
                                    height=30,
                                ) if paiement.get('statut') == 'EN_ATTENTE' else Text(""),
                            ],
                            spacing=5,
                        )),
                    ],
                )
            )
        
        return DataTable(
            columns=[
                DataColumn(label=Text("N° Transaction", weight=FontWeight.BOLD)),
                DataColumn(label=Text("N° Facture", weight=FontWeight.BOLD)),
                DataColumn(label=Text("Client", weight=FontWeight.BOLD)),
                DataColumn(label=Text("Montant", weight=FontWeight.BOLD)),
                DataColumn(label=Text("Statut", weight=FontWeight.BOLD)),
                DataColumn(label=Text("Actions", weight=FontWeight.BOLD)),
            ],
            rows=rows,
            expand=True,
        )
    
    def did_mount(self):
        """Appelé quand la page est montée - charge les données."""
        self._load_all_data(None)
    
    def _load_all_data(self, e):
        """Charge toutes les données."""
        self.loading.visible = True
        self.error_text.value = ""
        self.page.update()
        
        try:
            # Charger les statistiques
            self._load_statistiques()
            
            # Charger les données selon l'onglet
            self._load_tab_data(self.selected_tab)
        except APIError as e:
            self.error_text.value = f"Erreur: {e.message}"
        except Exception as e:
            self.error_text.value = f"Erreur: {str(e)}"
        finally:
            self.loading.visible = False
            self.page.update()
    
    def _load_statistiques(self):
        """Charge les statistiques globales."""
        try:
            # Statistiques financières
            stats_fin = api_client.get_statistiques_financieres()
            self.stats_data.update(stats_fin)
            
            # Statistiques cimetière
            stats_cim = api_client.get_statistiques()
            self.stats_data.update(stats_cim)
            
            # Compter les utilisateurs
            users = api_client.get_users() if hasattr(api_client, 'get_users') else []
            self.stats_data['total_users'] = len(users) if isinstance(users, list) else 0
            
        except Exception as e:
            logger.error(f"Erreur chargement statistiques: {str(e)}")
    
    def _load_tab_data(self, tab_index: int):
        """Charge les données pour un onglet spécifique."""
        try:
            if tab_index == 1:  # Utilisateurs
                self._load_users()
            elif tab_index == 2:  # Réservations
                self._load_reservations()
            elif tab_index == 3:  # Factures
                self._load_factures()
            elif tab_index == 4:  # Paiements
                self._load_paiements()
        except Exception as e:
            self.error_text.value = f"Erreur chargement données: {str(e)}"
            self.page.update()
    
    def _load_users(self):
        """Charge la liste des utilisateurs."""
        try:
            # Utiliser l'API admin si disponible, sinon l'API standard
            if hasattr(api_client, 'list_users'):
                self.users_data = api_client.list_users()
            else:
                self.users_data = []
        except Exception as e:
            self.error_text.value = f"Erreur chargement utilisateurs: {str(e)}"
    
    def _load_reservations(self):
        """Charge la liste des réservations."""
        try:
            if hasattr(api_client, 'list_reservations'):
                self.reservations_data = api_client.list_reservations()
            else:
                self.reservations_data = []
        except Exception as e:
            self.error_text.value = f"Erreur chargement réservations: {str(e)}"
    
    def _load_factures(self):
        """Charge la liste des factures."""
        try:
            if hasattr(api_client, 'list_factures'):
                self.factures_data = api_client.list_factures()
            else:
                self.factures_data = []
        except Exception as e:
            self.error_text.value = f"Erreur chargement factures: {str(e)}"
    
    def _load_paiements(self):
        """Charge la liste des paiements."""
        try:
            if hasattr(api_client, 'list_paiements'):
                self.paiements_data = api_client.list_paiements()
            else:
                self.paiements_data = []
        except Exception as e:
            self.error_text.value = f"Erreur chargement paiements: {str(e)}"
    
    # === Méthodes pour les dialogues ===
    
    def _show_add_user_dialog(self, e):
        """Affiche le dialogue d'ajout d'utilisateur."""
        # Ce sera implémenté dans la prochaine version
        self._show_message("Fonctionnalité à venir", "L'ajout d'utilisateur sera disponible prochainement.")
    
    def _show_edit_user_dialog(self, user_id, e=None):
        """Affiche le dialogue d'édition d'utilisateur."""
        self._show_message("Fonctionnalité à venir", f"L'édition de l'utilisateur {user_id} sera disponible prochainement.")
    
    def _confirm_delete_user(self, user_id, e=None):
        """Confirme la suppression d'un utilisateur."""
        self.page.open(
            AlertDialog(
                title=Text("Supprimer l'utilisateur"),
                content=Text(f"Êtes-vous sûr de vouloir supprimer l'utilisateur ? Cette action est irréversible."),
                actions=[
                    TextButton("Annuler", on_click=lambda _: self.page.close(self.page.overlay[-1])),
                    TextButton(
                        "Supprimer",
                        on_click=lambda _: self._delete_user(user_id),
                        style=ft.ButtonStyle(color=Colors.RED_500),
                    ),
                ],
            )
        )
    
    def _delete_user(self, user_id):
        """Supprime un utilisateur."""
        self.page.close(self.page.overlay[-1])
        try:
            if hasattr(api_client, 'delete_user'):
                result = api_client.delete_user(user_id)
                self._show_snackbar(result.get('message', 'Utilisateur supprimé'))
                self._load_users()
                self.page.update()
        except Exception as e:
            self._show_snackbar(f"Erreur: {str(e)}")
    
    def _confirm_valider_reservation(self, reservation_id, e=None):
        """Confirme la validation d'une réservation."""
        self.page.open(
            AlertDialog(
                title=Text("Valider la réservation"),
                content=Text("Êtes-vous sûr de vouloir valider cette réservation ? Une concession et une facture seront créées automatiquement."),
                actions=[
                    TextButton("Annuler", on_click=lambda _: self.page.close(self.page.overlay[-1])),
                    TextButton(
                        "Valider",
                        on_click=lambda _: self._valider_reservation(reservation_id),
                        style=ft.ButtonStyle(color=Colors.GREEN_500),
                    ),
                ],
            )
        )
    
    def _valider_reservation(self, reservation_id):
        """Valide une réservation."""
        self.page.close(self.page.overlay[-1])
        try:
            if hasattr(api_client, 'valider_reservation'):
                result = api_client.valider_reservation(reservation_id)
                self._show_snackbar(result.get('message', 'Réservation validée'))
                self._load_reservations()
                self.page.update()
        except Exception as e:
            self._show_snackbar(f"Erreur: {str(e)}")
    
    def _show_refuser_reservation_dialog(self, reservation_id, e=None):
        """Affiche le dialogue de refus de réservation."""
        motif_field = TextField(
            label="Motif du refus",
            multiline=True,
            min_lines=3,
            max_lines=5,
        )
        
        self.page.open(
            AlertDialog(
                title=Text("Refuser la réservation"),
                content=Column(
                    [
                        Text("Veuillez indiquer le motif du refus:"),
                        motif_field,
                    ],
                    tight=True,
                ),
                actions=[
                    TextButton("Annuler", on_click=lambda _: self.page.close(self.page.overlay[-1])),
                    TextButton(
                        "Refuser",
                        on_click=lambda _: self._refuser_reservation(reservation_id, motif_field.value),
                        style=ft.ButtonStyle(color=Colors.RED_500),
                    ),
                ],
            )
        )
    
    def _refuser_reservation(self, reservation_id, motif):
        """Refuse une réservation."""
        self.page.close(self.page.overlay[-1])
        if not motif:
            self._show_snackbar("Veuillez indiquer un motif de refus.")
            return
        
        try:
            if hasattr(api_client, 'refuser_reservation'):
                result = api_client.refuser_reservation(reservation_id, motif)
                self._show_snackbar(result.get('message', 'Réservation refusée'))
                self._load_reservations()
                self.page.update()
        except Exception as e:
            self._show_snackbar(f"Erreur: {str(e)}")
    
    def _confirm_marquer_payee(self, facture_id, e=None):
        """Confirme le marquage d'une facture comme payée."""
        self.page.open(
            AlertDialog(
                title=Text("Marquer comme payée"),
                content=Text("Êtes-vous sûr de vouloir marquer cette facture comme payée ?"),
                actions=[
                    TextButton("Annuler", on_click=lambda _: self.page.close(self.page.overlay[-1])),
                    TextButton(
                        "Confirmer",
                        on_click=lambda _: self._marquer_payee(facture_id),
                        style=ft.ButtonStyle(color=Colors.GREEN_500),
                    ),
                ],
            )
        )
    
    def _marquer_payee(self, facture_id):
        """Marque une facture comme payée."""
        self.page.close(self.page.overlay[-1])
        try:
            if hasattr(api_client, 'valider_paiement_facture'):
                result = api_client.valider_paiement_facture(facture_id)
                self._show_snackbar(result.get('message', 'Facture marquée comme payée'))
                self._load_factures()
                self.page.update()
        except Exception as e:
            self._show_snackbar(f"Erreur: {str(e)}")
    
    def _view_facture_pdf(self, facture_id, e=None):
        """Affiche le PDF d'une facture."""
        self._show_message("Fonctionnalité à venir", "L'affichage du PDF sera disponible prochainement.")
    
    def _confirm_valider_paiement(self, paiement_id, e=None):
        """Confirme la validation d'un paiement."""
        self.page.open(
            AlertDialog(
                title=Text("Valider le paiement"),
                content=Text("Êtes-vous sûr de vouloir valider ce paiement ?"),
                actions=[
                    TextButton("Annuler", on_click=lambda _: self.page.close(self.page.overlay[-1])),
                    TextButton(
                        "Valider",
                        on_click=lambda _: self._valider_paiement(paiement_id),
                        style=ft.ButtonStyle(color=Colors.GREEN_500),
                    ),
                ],
            )
        )
    
    def _valider_paiement(self, paiement_id):
        """Valide un paiement."""
        self.page.close(self.page.overlay[-1])
        try:
            if hasattr(api_client, 'valider_paiement'):
                result = api_client.valider_paiement(paiement_id)
                self._show_snackbar(result.get('message', 'Paiement validé'))
                self._load_paiements()
                self.page.update()
        except Exception as e:
            self._show_snackbar(f"Erreur: {str(e)}")
    
    def _show_refuser_paiement_dialog(self, paiement_id, e=None):
        """Affiche le dialogue de refus de paiement."""
        motif_field = TextField(
            label="Motif du refus",
            multiline=True,
            min_lines=3,
            max_lines=5,
        )
        
        self.page.open(
            AlertDialog(
                title=Text("Refuser le paiement"),
                content=Column(
                    [
                        Text("Veuillez indiquer le motif du refus:"),
                        motif_field,
                    ],
                    tight=True,
                ),
                actions=[
                    TextButton("Annuler", on_click=lambda _: self.page.close(self.page.overlay[-1])),
                    TextButton(
                        "Refuser",
                        on_click=lambda _: self._refuser_paiement(paiement_id, motif_field.value),
                        style=ft.ButtonStyle(color=Colors.RED_500),
                    ),
                ],
            )
        )
    
    def _refuser_paiement(self, paiement_id, motif):
        """Refuse un paiement."""
        self.page.close(self.page.overlay[-1])
        if not motif:
            self._show_snackbar("Veuillez indiquer un motif de refus.")
            return
        
        try:
            if hasattr(api_client, 'refuser_paiement'):
                result = api_client.refuser_paiement(paiement_id, motif)
                self._show_snackbar(result.get('message', 'Paiement refusé'))
                self._load_paiements()
                self.page.update()
        except Exception as e:
            self._show_snackbar(f"Erreur: {str(e)}")
    
    def _filter_users(self, e):
        """Filtre les utilisateurs."""
        self._load_users()
        self.page.update()
    
    def _filter_reservations(self, e):
        """Filtre les réservations."""
        self._load_reservations()
        self.page.update()
    
    def _filter_factures(self, e):
        """Filtre les factures."""
        self._load_factures()
        self.page.update()
    
    def _show_message(self, title: str, message: str):
        """Affiche un message dans une boîte de dialogue."""
        self.page.open(
            AlertDialog(
                title=Text(title),
                content=Text(message),
                actions=[
                    TextButton("OK", on_click=lambda _: self.page.close(self.page.overlay[-1]))
                ],
            )
        )
    
    def _show_snackbar(self, message: str):
        """Affiche un snackbar."""
        self.snackbar.content = Text(message)
        self.snackbar.open = True
        self.page.update()
