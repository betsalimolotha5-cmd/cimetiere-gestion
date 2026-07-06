"""
Page d'import/export de données.
"""
import flet as ft
from flet import (
    View, AppBar, Container, Column, Row, Text, Icon, Icons, Colors,
    FontWeight, TextAlign, Card, Divider, IconButton, CircleAvatar,
    PopupMenuButton, PopupMenuItem, ElevatedButton, FilePicker,
    FilePickerFileType, border_radius, alignment, padding
)
from frontend.api_client import api_client, APIError
from frontend.theme import AppColors


class ImportExportPage:
    """Page d'import/export."""
    
    def __init__(self, page: ft.Page, app_state):
        self.page = page
        self.app_state = app_state
        
        # File pickers
        self.file_picker_zones = FilePicker(on_result=self._on_file_picked_zones)
        self.file_picker_caveaux = FilePicker(on_result=self._on_file_picked_caveaux)
        self.file_picker_defunts = FilePicker(on_result=self._on_file_picked_defunts)
        
        self.result_text = Text("", size=13)
        self.loading = ft.ProgressRing(visible=False)
    
    def build(self) -> View:
        """Construit la vue."""
        return View(
            "/import-export",
            [
                self._create_app_bar("Import/Export"),
                Container(
                    content=Column([
                        # En-tête
                        Text("📥📤 Import/Export de données", size=24, weight=FontWeight.BOLD),
                        Text("Importez ou exportez vos données en CSV", size=13, color=AppColors.TEXT_SECONDARY),
                        Divider(height=20),
                        
                        # Section IMPORT
                        Text("📥 IMPORT CSV", size=18, weight=FontWeight.BOLD, color=Colors.BLUE),
                        Row([
                            self._create_import_card(
                                "🗺️ Zones",
                                "Importer des zones depuis un CSV",
                                Icons.MAP,
                                Colors.BLUE,
                                lambda _: self.file_picker_zones.pick_files(
                                    allowed_extensions=["csv"],
                                    allow_multiple=False
                                )
                            ),
                            self._create_import_card(
                                "⚰️ Caveaux",
                                "Importer des caveaux depuis un CSV",
                                Icons.LOCATION_CITY,
                                Colors.PURPLE,
                                lambda _: self.file_picker_caveaux.pick_files(
                                    allowed_extensions=["csv"],
                                    allow_multiple=False
                                )
                            ),
                            self._create_import_card(
                                "👤 Défunts",
                                "Importer des défunts depuis un CSV",
                                Icons.PERSON,
                                Colors.TEAL,
                                lambda _: self.file_picker_defunts.pick_files(
                                    allowed_extensions=["csv"],
                                    allow_multiple=False
                                )
                            ),
                        ], wrap=True, spacing=15),
                        
                        Divider(height=30),
                        
                        # Section EXPORT
                        Text("📤 EXPORT CSV", size=18, weight=FontWeight.BOLD, color=Colors.GREEN),
                        Row([
                            self._create_export_card(
                                "🗺️ Zones",
                                "Exporter toutes les zones",
                                Icons.MAP,
                                Colors.BLUE,
                                lambda _: self._exporter("zones")
                            ),
                            self._create_export_card(
                                "⚰️ Caveaux",
                                "Exporter tous les caveaux",
                                Icons.LOCATION_CITY,
                                Colors.PURPLE,
                                lambda _: self._exporter("caveaux")
                            ),
                            self._create_export_card(
                                "📋 Concessions",
                                "Exporter toutes les concessions",
                                Icons.DESCRIPTION,
                                Colors.ORANGE,
                                lambda _: self._exporter("concessions")
                            ),
                            self._create_export_card(
                                "👤 Défunts",
                                "Exporter tous les défunts",
                                Icons.PERSON,
                                Colors.TEAL,
                                lambda _: self._exporter("defunts")
                            ),
                        ], wrap=True, spacing=15),
                        
                        Divider(height=30),
                        
                        # Modèles CSV
                        Text("📝 Modèles CSV", size=18, weight=FontWeight.BOLD),
                        Container(
                            content=Column([
                                Text("Téléchargez les modèles pour préparer vos imports :", size=13),
                                Row([
                                    ElevatedButton(
                                        "📥 Modèle Zones",
                                        icon=Icons.DOWNLOAD,
                                        on_click=lambda _: self._telecharger_modele("zones")
                                    ),
                                    ElevatedButton(
                                        "📥 Modèle Caveaux",
                                        icon=Icons.DOWNLOAD,
                                        on_click=lambda _: self._telecharger_modele("caveaux")
                                    ),
                                    ElevatedButton(
                                        "📥 Modèle Défunts",
                                        icon=Icons.DOWNLOAD,
                                        on_click=lambda _: self._telecharger_modele("defunts")
                                    ),
                                ], wrap=True, spacing=10),
                            ]),
                            padding=20,
                            bgcolor=Colors.WHITE,
                            border_radius=border_radius.all(12),
                        ),
                        
                        Divider(height=20),
                        self.result_text,
                        self.loading,
                    ], spacing=10, expand=True, scroll=ft.ScrollMode.AUTO),
                    padding=20,
                    expand=True,
                    bgcolor=AppColors.BACKGROUND,
                ),
            ],
            overlay=[self.file_picker_zones, self.file_picker_caveaux, self.file_picker_defunts],
        )
    
    def _create_import_card(self, title, description, icon, color, on_click):
        """Crée une carte d'import."""
        return Card(
            content=Container(
                content=Column([
                    Icon(icon, size=40, color=color),
                    Text(title, size=16, weight=FontWeight.BOLD),
                    Text(description, size=12, color=AppColors.TEXT_SECONDARY, text_align=TextAlign.CENTER),
                    ElevatedButton(
                        "📥 Importer",
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
    
    def _create_export_card(self, title, description, icon, color, on_click):
        """Crée une carte d'export."""
        return Card(
            content=Container(
                content=Column([
                    Icon(icon, size=40, color=color),
                    Text(title, size=16, weight=FontWeight.BOLD),
                    Text(description, size=12, color=AppColors.TEXT_SECONDARY, text_align=TextAlign.CENTER),
                    ElevatedButton(
                        "📤 Exporter",
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
    
    def _on_file_picked_zones(self, e):
        """Gère le fichier sélectionné pour les zones."""
        if e.files:
            self._importer("zones", e.files[0].path)
    
    def _on_file_picked_caveaux(self, e):
        """Gère le fichier sélectionné pour les caveaux."""
        if e.files:
            self._importer("caveaux", e.files[0].path)
    
    def _on_file_picked_defunts(self, e):
        """Gère le fichier sélectionné pour les défunts."""
        if e.files:
            self._importer("defunts", e.files[0].path)
    
    def _importer(self, type_data, file_path):
        """Importe les données."""
        self.loading.visible = True
        self.page.update()
        
        try:
            with open(file_path, 'rb') as f:
                result = api_client.importer_csv(type_data, f)
                
                if result.get('success'):
                    self.result_text.value = f"✅ Import réussi : {result.get('imported', 0)} élément(s) importé(s)"
                    self.result_text.color = AppColors.SUCCESS
                else:
                    self.result_text.value = f"❌ Erreur : {result.get('errors', 0)} erreur(s)"
                    self.result_text.color = Colors.RED_400
        except Exception as e:
            self.result_text.value = f"❌ Erreur : {str(e)}"
            self.result_text.color = Colors.RED_400
        finally:
            self.loading.visible = False
            self.page.update()
    
    def _exporter(self, type_data):
        """Exporte les données."""
        try:
            url = f"http://localhost:8000/api/core/export/{type_data}"
            self.page.launch_url(url)
            self.result_text.value = f"✅ Export {type_data} lancé"
            self.result_text.color = AppColors.SUCCESS
        except Exception as e:
            self.result_text.value = f"❌ Erreur : {str(e)}"
            self.result_text.color = Colors.RED_400
        self.page.update()
    
    def _telecharger_modele(self, type_data):
        """Télécharge un modèle CSV."""
        modeles = {
            'zones': "code,nom,type_zone,est_exploitable,superficie\nZ01,Zone Nord,SECTION,True,500.00",
            'caveaux': "code,numero,zone_code,type_caveau,longueur,largeur,profondeur,prix_concession\nC001,1A,Z01,INDIVIDUEL,2.5,1.2,1.5,5000",
            'defunts': "nom,prenom,date_naissance,date_deces,sexe,numero_identite\nDUPONT,Jean,1940-05-15,2024-01-10,M,123456789",
        }
        
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write(modeles.get(type_data, ''))
            temp_path = f.name
        
        self.page.launch_url(f"file://{temp_path}")
        self.result_text.value = f"✅ Modèle {type_data} téléchargé"
        self.result_text.color = AppColors.SUCCESS
        self.page.update()
    
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