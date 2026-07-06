"""
Page de la carte interactive du cimetière.
Affiche les caveaux sous forme de grille visuelle avec filtres.
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
    ElevatedButton,
    OutlinedButton,
    border_radius,
    alignment,
    padding,
)
from frontend.api_client import api_client, APIError
from frontend.theme import AppColors, AppSpacing, AppComponents


class CartePage:
    """Page de la carte interactive du cimetière."""
    
    # Couleurs des statuts de caveaux
    STATUT_COLORS = {
        'DISPONIBLE': AppColors.STATUS_DISPONIBLE,
        'RESERVE': AppColors.STATUS_RESERVE,
        'OCCUPE': AppColors.STATUS_OCCUPE,
        'NON_EXPLOITABLE': AppColors.STATUS_NON_EXPLOITABLE,
    }
    
    def __init__(self, page: ft.Page, app_state):
        self.page = page
        self.app_state = app_state
        
        # Données
        self.caveaux = []
        self.zones = []
        self.selected_caveau = None
        self.filtered_caveaux = []
        
        # Filtres
        self.zone_filter = Dropdown(
            label="Zone",
            width=200,
            border_radius=border_radius.all(10),
            options=[dropdown.Option(key="", text="Toutes les zones")],
            on_change=self._on_filter_changed,
        )
        
        self.statut_filter = Dropdown(
            label="Statut",
            width=180,
            border_radius=border_radius.all(10),
            options=[
                dropdown.Option(key="", text="Tous les statuts"),
                dropdown.Option(key="DISPONIBLE", text="🟢 Disponible"),
                dropdown.Option(key="RESERVE", text="🟠 Réservé"),
                dropdown.Option(key="OCCUPE", text="🔴 Occupé"),
                dropdown.Option(key="NON_EXPLOITABLE", text="⚫ Non exploitable"),
            ],
            on_change=self._on_filter_changed,
        )
        
        self.search_field = TextField(
            label="Rechercher un caveau...",
            prefix_icon=Icons.SEARCH,
            width=250,
            border_radius=border_radius.all(10),
            on_change=self._on_filter_changed,
        )
        
        # Conteneur de la grille de caveaux
        self.caveaux_grid = ft.GridView(
            expand=1,
            runs_count=6,
            max_extent=120,
            child_aspect_ratio=1.0,
            spacing=10,
            run_spacing=10,
            padding=10,
        )
        
        # Panneau de détails
        self.detail_panel = Container(
            content=self._build_empty_detail(),
            width=350,
            padding=20,
            bgcolor=Colors.WHITE,
            border_radius=border_radius.all(12),
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=8,
                color=Colors.with_opacity(0.15, Colors.BLACK),
                offset=ft.Offset(0, 3),
            ),
        )
        
        # Compteurs
        self.count_text = Text("", size=13, color=AppColors.TEXT_SECONDARY)
        
        # Chargement
        self.loading = ft.ProgressRing(visible=False)
    
    def build(self) -> View:
        """Construit la vue de la carte."""
        
        return View(
            "/carte",
            [
                self._create_app_bar("Carte Interactive"),
                Container(
                    content=Column(
                        [
                            # En-tête avec filtres
                            self._build_filters_bar(),
                            
                            Divider(height=15),
                            
                            # Légende
                            self._build_legend(),
                            
                            Divider(height=15),
                            
                            # Compteurs et indicateur de chargement
                            Row(
                                [
                                    self.count_text,
                                    self.loading,
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            
                            Divider(height=10),
                            
                            # Contenu principal : grille + détails
                            Row(
                                [
                                    # Grille des caveaux
                                    Container(
                                        content=self.caveaux_grid,
                                        expand=True,
                                        bgcolor=Colors.WHITE,
                                        border_radius=border_radius.all(12),
                                        padding=10,
                                        shadow=ft.BoxShadow(
                                            spread_radius=1,
                                            blur_radius=5,
                                            color=Colors.with_opacity(0.1, Colors.BLACK),
                                            offset=ft.Offset(0, 2),
                                        ),
                                    ),
                                    
                                    # Panneau de détails
                                    self.detail_panel,
                                ],
                                expand=True,
                                spacing=20,
                                vertical_alignment=ft.CrossAxisAlignment.START,
                            ),
                        ],
                        spacing=5,
                        expand=True,
                    ),
                    padding=20,
                    expand=True,
                    bgcolor=AppColors.BACKGROUND,
                ),
                self._create_navigation_bar(),
            ],
        )
    
    def _build_filters_bar(self) -> Container:
        """Construit la barre de filtres."""
        return Container(
            content=Row(
                [
                    Icon(Icons.FILTER_LIST, color=AppColors.PRIMARY),
                    Text("Filtres :", weight=FontWeight.BOLD, size=14),
                    self.zone_filter,
                    self.statut_filter,
                    self.search_field,
                    IconButton(
                        Icons.CLEAR_ALL,
                        tooltip="Réinitialiser les filtres",
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
        )
    
    def _build_legend(self) -> Container:
        """Construit la légende des couleurs."""
        def legend_item(color: str, label: str) -> Row:
            return Row(
                [
                    Container(
                        width=20,
                        height=20,
                        bgcolor=color,
                        border_radius=border_radius.all(4),
                    ),
                    Text(label, size=12),
                ],
                spacing=8,
            )
        
        return Container(
            content=Row(
                [
                    Text("Légende :", weight=FontWeight.BOLD, size=13),
                    legend_item(AppColors.STATUS_DISPONIBLE, "Disponible"),
                    legend_item(AppColors.STATUS_RESERVE, "Réservé"),
                    legend_item(AppColors.STATUS_OCCUPE, "Occupé"),
                    legend_item(AppColors.STATUS_NON_EXPLOITABLE, "Non exploitable"),
                ],
                spacing=20,
                wrap=True,
            ),
            padding=10,
            bgcolor=Colors.WHITE,
            border_radius=border_radius.all(8),
        )
    
    def _build_caveau_cell(self, caveau: dict) -> Container:
        """Construit une cellule visuelle pour un caveau."""
        statut = caveau.get('statut', 'DISPONIBLE')
        code = caveau.get('code', '?')
        color = self.STATUT_COLORS.get(statut, Colors.GREY)
        is_reservable = caveau.get('reservable', False)
        
        def on_tap(e):
            self._show_caveau_details(caveau)
        
        return Container(
            content=Column(
                [
                    Text(
                        code,
                        size=13,
                        weight=FontWeight.BOLD,
                        color=Colors.WHITE,
                        text_align=TextAlign.CENTER,
                    ),
                    Text(
                        caveau.get('type_caveau', ''),
                        size=9,
                        color=Colors.with_opacity(0.8, Colors.WHITE),
                        text_align=TextAlign.CENTER,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
            ),
            width=100,
            height=80,
            bgcolor=color,
            border_radius=border_radius.all(10),
            alignment=alignment.center,
            on_click=on_tap,
            tooltip=f"{code} - {statut.replace('_', ' ').title()}",
            ink=True,
            animate_opacity=ft.animation.Animation(300, ft.AnimationCurve.EASE_IN_OUT),
            on_hover=lambda e, c=color: self._on_caveau_hover(e, c),
        )
    
    def _on_caveau_hover(self, e, original_color):
        """Effet de survol sur les caveaux."""
        if e.data == "true":
            e.control.bgcolor = Colors.with_opacity(0.7, original_color)
        else:
            e.control.bgcolor = original_color
        e.control.update()
    
    def _build_empty_detail(self) -> Column:
        """Panneau de détails vide."""
        return Column(
            [
                Icon(Icons.TOUCH_APP, size=48, color=AppColors.TEXT_SECONDARY),
                Text(
                    "Sélectionnez un caveau\npour voir les détails",
                    size=14,
                    color=AppColors.TEXT_SECONDARY,
                    text_align=TextAlign.CENTER,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=15,
        )
    
    def _build_caveau_detail(self, caveau: dict) -> Column:
        """Construit le panneau de détails d'un caveau."""
        statut = caveau.get('statut', 'DISPONIBLE')
        statut_display = caveau.get('statut_display', statut)
        color = self.STATUT_COLORS.get(statut, Colors.GREY)
        
        # Bouton de réservation
        reserve_button = ElevatedButton(
            "📝 Réserver ce caveau",
            icon=Icons.BOOKMARK_ADD,
            bgcolor=AppColors.PRIMARY,
            color=Colors.WHITE,
            width=280,
            on_click=lambda _: self._on_reserver(caveau),
        ) if caveau.get('reservable') else Text(
            "Ce caveau n'est pas réservable",
            size=12,
            color=AppColors.TEXT_SECONDARY,
            italic=True,
        )
        
        return Column(
            [
                # En-tête du détail
                Row(
                    [
                        Text(
                            f"Caveau {caveau.get('code', '?')}",
                            size=20,
                            weight=FontWeight.BOLD,
                        ),
                        IconButton(
                            Icons.CLOSE,
                            icon_size=20,
                            on_click=lambda _: self._clear_detail(),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                
                # Badge de statut
                Container(
                    content=Text(
                        statut_display,
                        size=12,
                        weight=FontWeight.BOLD,
                        color=Colors.WHITE,
                    ),
                    bgcolor=color,
                    padding=ft.padding.symmetric(horizontal=15, vertical=5),
                    border_radius=border_radius.all(20),
                ),
                
                Divider(height=20),
                
                # Informations
                self._detail_row("Zone", f"{caveau.get('zone_code', '?')}"),
                self._detail_row("Type", caveau.get('type_caveau', 'N/A').replace('_', ' ').title()),
                self._detail_row("Dimensions", f"{caveau.get('longueur', '?')}m × {caveau.get('largeur', '?')}m"),
                self._detail_row("Profondeur", f"{caveau.get('profondeur', '?')}m"),
                
                Divider(height=15),
                
                # Prix
                Text("💰 Tarifs", size=14, weight=FontWeight.BOLD),
                self._detail_row("Concession", f"{caveau.get('prix_concession', '0'):,.2f} FC"),
                self._detail_row("Perpétuité", f"{caveau.get('prix_perpetuite', '0'):,.2f} FC"),
                
                Divider(height=20),
                
                # Bouton de réservation
                reserve_button,
            ],
            spacing=10,
        )
    
    def _detail_row(self, label: str, value: str) -> Row:
        """Crée une ligne de détail."""
        return Row(
            [
                Text(f"{label} :", size=13, color=AppColors.TEXT_SECONDARY, width=100),
                Text(value, size=13, weight=FontWeight.W_500),
            ],
            spacing=10,
        )
    
    def _show_caveau_details(self, caveau: dict):
        """Affiche les détails d'un caveau."""
        self.selected_caveau = caveau
        self.detail_panel.content = self._build_caveau_detail(caveau)
        self.page.update()
    
    def _clear_detail(self):
        """Efface le panneau de détails."""
        self.selected_caveau = None
        self.detail_panel.content = self._build_empty_detail()
        self.page.update()
    
    def _on_filter_changed(self, e):
        """Applique les filtres sur la liste des caveaux."""
        zone = self.zone_filter.value or ""
        statut = self.statut_filter.value or ""
        search = (self.search_field.value or "").lower()
        
        filtered = self.caveaux
        
        if zone:
            filtered = [c for c in filtered if c.get('zone_id') == int(zone) or c.get('zone_code') == zone]
        
        if statut:
            filtered = [c for c in filtered if c.get('statut') == statut]
        
        if search:
            filtered = [c for c in filtered if search in c.get('code', '').lower()]
        
        self.filtered_caveaux = filtered
        self._render_grid()
    
    def _reset_filters(self, e):
        """Réinitialise tous les filtres."""
        self.zone_filter.value = ""
        self.statut_filter.value = ""
        self.search_field.value = ""
        self.filtered_caveaux = self.caveaux
        self._render_grid()
        self.page.update()
    
    def _render_grid(self):
        """Rendu de la grille de caveaux."""
        self.caveaux_grid.controls = [
            self._build_caveau_cell(caveau) for caveau in self.filtered_caveaux
        ]
        
        # Compteurs
        total = len(self.filtered_caveaux)
        dispo = sum(1 for c in self.filtered_caveaux if c.get('statut') == 'DISPONIBLE')
        self.count_text.value = f"Affichage : {total} caveau(x) dont {dispo} disponible(s)"
        
        self.page.update()
    
    def _on_reserver(self, caveau: dict):
        """Lance le processus de réservation."""
        if caveau.get('statut') != 'DISPONIBLE':
            self._show_dialog("Erreur", "Ce caveau n'est pas disponible.")
            return
        
        # Ouvrir un formulaire de réservation
        defunt_nom = TextField(label="Nom du défunt", border_radius=border_radius.all(10))
        defunt_prenom = TextField(label="Prénom du défunt", border_radius=border_radius.all(10))
        defunt_date_deces = TextField(
            label="Date de décès (AAAA-MM-JJ)",
            border_radius=border_radius.all(10),
        )
        
        error_text = Text("", color=Colors.RED_400, size=12)
        
        def submit_reservation(e):
            if not defunt_nom.value or not defunt_prenom.value or not defunt_date_deces.value:
                error_text.value = "Tous les champs sont obligatoires"
                self.page.update()
                return
            
            try:
                result = api_client.create_reservation(
                    caveau_id=caveau.get('id'),
                    defunt_nom=defunt_nom.value,
                    defunt_prenom=defunt_prenom.value,
                    defunt_date_deces=defunt_date_deces.value,
                )
                
                self.page.close(dialog)
                self._show_dialog(
                    "✅ Réservation enregistrée",
                    f"Votre réservation pour le caveau {caveau.get('code')} a été enregistrée.\n"
                    f"N° de contrat : {result.get('data', {}).get('numero_contrat', 'N/A')}\n\n"
                    f"Elle est en attente de validation par l'administration.",
                )
                
                # Recharger les données
                self._load_data()
                
            except APIError as err:
                error_text.value = f"Erreur : {err.message}"
                self.page.update()
        
        dialog = ft.AlertDialog(
            title=Text(f"Réserver le caveau {caveau.get('code')}"),
            content=Column(
                [
                    Text("Informations du défunt", size=14, weight=FontWeight.BOLD),
                    defunt_nom,
                    defunt_prenom,
                    defunt_date_deces,
                    error_text,
                ],
                spacing=10,
                tight=True,
            ),
            actions=[
                ft.TextButton("Annuler", on_click=lambda _: self.page.close(dialog)),
                ElevatedButton(
                    "Confirmer la réservation",
                    bgcolor=AppColors.PRIMARY,
                    color=Colors.WHITE,
                    on_click=submit_reservation,
                ),
            ],
        )
        
        self.page.open(dialog)
    
    def _show_dialog(self, title: str, message: str):
        """Affiche une boîte de dialogue."""
        self.page.open(
            ft.AlertDialog(
                title=Text(title),
                content=Text(message),
                actions=[
                    ft.TextButton("OK", on_click=lambda _: self.page.close(self.page.overlay[-1]))
                ],
            )
        )
    
    def _load_data(self):
        """Charge les données depuis l'API."""
        self.loading.visible = True
        self.page.update()
        
        try:
            # Charger les zones
            self.zones = api_client.get_zones()
            
            # Mettre à jour le filtre des zones
            self.zone_filter.options = [dropdown.Option(key="", text="Toutes les zones")]
            for zone in self.zones:
                self.zone_filter.options.append(
                    dropdown.Option(
                        key=str(zone.get('id')),
                        text=f"{zone.get('code')} - {zone.get('nom')}"
                    )
                )
            
            # Charger les caveaux
            self.caveaux = api_client.get_caveaux()
            self.filtered_caveaux = self.caveaux
            
            # Rendre la grille
            self._render_grid()
            
        except APIError as e:
            self.count_text.value = f"Erreur de chargement : {e.message}"
        except Exception as e:
            self.count_text.value = f"Erreur : {str(e)}"
        finally:
            self.loading.visible = False
            self.page.update()
    
    def did_mount(self):
        """Appelé quand la page est montée."""
        self._load_data()
    
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
            selected_index=1,
            destinations=[
                NavigationBarDestination(icon=Icons.DASHBOARD, label="Accueil"),
                NavigationBarDestination(icon=Icons.MAP, label="Carte"),
                NavigationBarDestination(icon=Icons.BOOKMARK, label="Réservations"),
                NavigationBarDestination(icon=Icons.RECEIPT, label="Factures"),
            ],
            on_change=handle_change,
            bgcolor=Colors.WHITE,
        )