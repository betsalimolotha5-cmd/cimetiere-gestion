"""
Page des rapports et statistiques avancées.
"""
import flet as ft
from flet import (
    View, AppBar, Container, Column, Row, Text, Icon, Icons, Colors,
    FontWeight, TextAlign, Card, Divider, IconButton, CircleAvatar,
    NavigationBar, NavigationBarDestination, PopupMenuButton, PopupMenuItem,
    Dropdown, dropdown, DatePicker, ElevatedButton, OutlinedButton,
    border_radius, alignment, padding
)
from frontend.api_client import api_client, APIError
from frontend.theme import AppColors


class ReportsPage:
    """Page des rapports."""
    
    def __init__(self, page: ft.Page, app_state):
        self.page = page
        self.app_state = app_state
        
        # Filtres
        self.type_rapport = Dropdown(
            label="Type de rapport",
            width=250,
            border_radius=border_radius.all(10),
            options=[
                dropdown.Option(key="occupation", text="📊 Taux d'occupation"),
                dropdown.Option(key="financier", text="💰 Rapport financier"),
                dropdown.Option(key="concessions", text="📋 Concessions"),
                dropdown.Option(key="defunts", text="👤 Défunts"),
                dropdown.Option(key="expirations", text="⏰ Expirations"),
            ],
            value="occupation",
        )
        
        self.format_export = Dropdown(
            label="Format d'export",
            width=200,
            border_radius=border_radius.all(10),
            options=[
                dropdown.Option(key="PDF", text="📄 PDF"),
                dropdown.Option(key="EXCEL", text="📊 Excel"),
                dropdown.Option(key="CSV", text="📋 CSV"),
            ],
            value="PDF",
        )
        
        self.date_debut = TextField(
            label="Date début (AAAA-MM-JJ)",
            width=200,
            border_radius=border_radius.all(10),
        )
        
        self.date_fin = TextField(
            label="Date fin (AAAA-MM-JJ)",
            width=200,
            border_radius=border_radius.all(10),
        )
        
        self.result_text = Text("", size=13, color=AppColors.TEXT_SECONDARY)
        self.loading = ft.ProgressRing(visible=False)
    
    def build(self) -> View:
        """Construit la vue des rapports."""
        return View(
            "/reports",
            [
                self._create_app_bar("Rapports"),
                Container(
                    content=Column(
                        [
                            # En-tête
                            Row(
                                [
                                    Column([
                                        Text("📊 Rapports & Statistiques", size=24, weight=FontWeight.BOLD),
                                        Text("Générez et exportez vos rapports", size=13, color=AppColors.TEXT_SECONDARY),
                                    ]),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            Divider(height=20),
                            
                            # Cartes de rapports rapides
                            Row([
                                self._create_rapport_card(
                                    "📊 Occupation", 
                                    "Taux d'occupation du cimetière",
                                    Icons.PIE_CHART,
                                    Colors.BLUE,
                                    lambda _: self._generer_rapport("occupation")
                                ),
                                self._create_rapport_card(
                                    "💰 Financier",
                                    "Revenus et paiements",
                                    Icons.ACCOUNT_BALANCE,
                                    Colors.GREEN,
                                    lambda _: self._generer_rapport("financier")
                                ),
                                self._create_rapport_card(
                                    "📋 Concessions",
                                    "Liste des concessions",
                                    Icons.DESCRIPTION,
                                    Colors.PURPLE,
                                    lambda _: self._generer_rapport("concessions")
                                ),
                                self._create_rapport_card(
                                    "⏰ Expirations",
                                    "Concessions à renouveler",
                                    Icons.WARNING,
                                    Colors.ORANGE,
                                    lambda _: self._generer_rapport("expirations")
                                ),
                            ], wrap=True, spacing=15),
                            
                            Divider(height=30),
                            
                            # Formulaire de génération
                            Container(
                                content=Column([
                                    Text("🎯 Génération personnalisée", size=18, weight=FontWeight.BOLD),
                                    Row([
                                        self.type_rapport,
                                        self.format_export,
                                    ], spacing=15),
                                    Row([
                                        self.date_debut,
                                        self.date_fin,
                                    ], spacing=15),
                                    Divider(height=15),
                                    self.result_text,
                                    self.loading,
                                    ElevatedButton(
                                        "📥 Générer et télécharger",
                                        icon=Icons.DOWNLOAD,
                                        bgcolor=AppColors.PRIMARY,
                                        color=Colors.WHITE,
                                        width=300,
                                        on_click=self._generer_rapport_personnalise,
                                    ),
                                ], spacing=15, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                                padding=30,
                                bgcolor=Colors.WHITE,
                                border_radius=border_radius.all(12),
                            ),
                            
                            Divider(height=30),
                            
                            # Historique des rapports
                            Text("📜 Historique des rapports générés", size=18, weight=FontWeight.BOLD),
                            self._build_historique(),
                        ],
                        spacing=10,
                        expand=True,
                        scroll=ft.ScrollMode.AUTO,
                    ),
                    padding=20,
                    expand=True,
                    bgcolor=AppColors.BACKGROUND,
                ),
            ],
        )
    
    def _create_rapport_card(self, title, description, icon, color, on_click):
        """Crée une carte de rapport rapide."""
        return Card(
            content=Container(
                content=Column([
                    Icon(icon, size=40, color=color),
                    Text(title, size=16, weight=FontWeight.BOLD),
                    Text(description, size=12, color=AppColors.TEXT_SECONDARY, text_align=TextAlign.CENTER),
                    ElevatedButton(
                        "Générer PDF",
                        bgcolor=color,
                        color=Colors.WHITE,
                        on_click=on_click,
                    ),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                padding=20,
                width=220,
                height=220,
                border_radius=border_radius.all(12),
            ),
            elevation=3,
        )
    
    def _build_historique(self):
        """Construit l'historique des rapports."""
        try:
            rapports = api_client.get_rapports_generes()
            if not rapports:
                return Text("Aucun rapport généré récemment", 
                          color=AppColors.TEXT_SECONDARY, italic=True)
            
            rows = []
            for r in rapports[:10]:
                rows.append(ft.ListTile(
                    leading=Icon(Icons.DESCRIPTION, color=AppColors.PRIMARY),
                    title=Text(r.get('titre', 'Rapport')),
                    subtitle=Text(f"{r.get('date_generation', '')} - {r.get('format_export', '')}"),
                    trailing=IconButton(Icons.DOWNLOAD, on_click=lambda _, r=r: self._telecharger_rapport(r)),
                ))
            
            return Column(rows, spacing=0)
        except Exception:
            return Text("Impossible de charger l'historique", color=Colors.RED_400)
    
    def _generer_rapport(self, type_rapport):
        """Génère un rapport rapide en PDF."""
        self.loading.visible = True
        self.page.update()
        
        try:
            url_map = {
                'occupation': '/api/reports/occupation/pdf',
                'financier': '/api/reports/financier/pdf',
                'concessions': '/api/reports/concessions/pdf',
                'expirations': '/api/reports/concessions/pdf?statut=ACTIVE',
            }
            
            url = url_map.get(type_rapport)
            if url:
                self.result_text.value = f"✅ Rapport {type_rapport} généré avec succès"
                self.result_text.color = AppColors.SUCCESS
                # Le téléchargement se fait via le navigateur
                self.page.launch_url(f"http://localhost:8000{url}")
        except Exception as e:
            self.result_text.value = f"❌ Erreur : {str(e)}"
            self.result_text.color = Colors.RED_400
        finally:
            self.loading.visible = False
            self.page.update()
    
    def _generer_rapport_personnalise(self, e):
        """Génère un rapport personnalisé."""
        type_rapport = self.type_rapport.value
        format_export = self.format_export.value
        
        self.loading.visible = True
        self.page.update()
        
        try:
            url_map = {
                ('occupation', 'PDF'): '/api/reports/occupation/pdf',
                ('occupation', 'EXCEL'): '/api/reports/occupation/excel',
                ('occupation', 'CSV'): '/api/reports/occupation/csv',
                ('financier', 'PDF'): '/api/reports/financier/pdf',
                ('financier', 'EXCEL'): '/api/reports/financier/excel',
                ('concessions', 'PDF'): '/api/reports/concessions/pdf',
                ('concessions', 'EXCEL'): '/api/reports/concessions/excel',
            }
            
            url = url_map.get((type_rapport, format_export))
            if url:
                self.page.launch_url(f"http://localhost:8000{url}")
                self.result_text.value = f"✅ Rapport {type_rapport} ({format_export}) généré"
                self.result_text.color = AppColors.SUCCESS
            else:
                self.result_text.value = "❌ Format non disponible pour ce type de rapport"
                self.result_text.color = Colors.RED_400
        except Exception as e:
            self.result_text.value = f"❌ Erreur : {str(e)}"
            self.result_text.color = Colors.RED_400
        finally:
            self.loading.visible = False
            self.page.update()
    
    def _telecharger_rapport(self, rapport):
        """Télécharge un rapport depuis l'historique."""
        url = rapport.get('fichier_url')
        if url:
            self.page.launch_url(url)
    
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
                IconButton(Icons.NOTIFICATIONS, on_click=lambda _: self.page.go("/notifications")),
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