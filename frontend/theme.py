"""
Thème et styles globaux de l'application Flet.
Définit l'identité visuelle et les composants réutilisables.
"""
import flet as ft
from flet import (
    Theme,
    Colors,
    FontWeight,
    TextAlign,
    BorderRadius,
    BoxShadow,
    Shadow,
    Offset,
    Blur,
    TextTheme,
    TextStyle,
    InputDecorationTheme,
    ElevatedButtonStyle,
    OutlinedButtonStyle,
    TextButtonStyle,
    FilledButtonStyle,
    IconButtonStyle,
    CardTheme,
    AppBarTheme,
    NavigationBarTheme,
    NavigationBarLabelBehavior,
    NavigationDestination,
)


# === COULEURS DU THÈME ===

class AppColors:
    """Palette de couleurs de l'application."""
    
    # Couleurs principales
    PRIMARY = "#2E7D32"          # Vert foncé (principal)
    PRIMARY_LIGHT = "#4CAF50"    # Vert clair
    PRIMARY_DARK = "#1B5E20"     # Vert très foncé
    
    # Couleurs secondaires
    SECONDARY = "#FFA000"        # Orange (accent)
    SECONDARY_LIGHT = "#FFC107"  # Jaune
    SECONDARY_DARK = "#FF6F00"   # Orange foncé
    
    # Couleurs de statut (pour les caveaux)
    STATUS_DISPONIBLE = "#4CAF50"     # Vert
    STATUS_RESERVE = "#FF9800"        # Orange
    STATUS_OCCUPE = "#F44336"         # Rouge
    STATUS_NON_EXPLOITABLE = "#9E9E9E"  # Gris
    
    # Couleurs neutres
    BACKGROUND = "#FAFAFA"       # Fond principal
    SURFACE = "#FFFFFF"          # Surface des cartes
    TEXT_PRIMARY = "#212121"     # Texte principal
    TEXT_SECONDARY = "#757575"   # Texte secondaire
    DIVIDER = "#E0E0E0"          # Lignes de séparation
    
    # Couleurs sémantiques
    SUCCESS = "#4CAF50"          # Succès
    WARNING = "#FF9800"          # Avertissement
    ERROR = "#F44336"            # Erreur
    INFO = "#2196F3"             # Information
    
    # Couleurs pour les rôles
    ROLE_ADMIN = "#9C27B0"       # Violet
    ROLE_AGENT = "#2196F3"       # Bleu
    ROLE_SECRETARY = "#00BCD4"   # Cyan
    ROLE_CLIENT = "#4CAF50"      # Vert


# === TYPOGRAPHIE ===

class AppTypography:
    """Styles de texte de l'application."""
    
    # Titres
    H1 = TextStyle(
        size=32,
        weight=FontWeight.BOLD,
        color=AppColors.TEXT_PRIMARY,
    )
    
    H2 = TextStyle(
        size=24,
        weight=FontWeight.BOLD,
        color=AppColors.TEXT_PRIMARY,
    )
    
    H3 = TextStyle(
        size=20,
        weight=FontWeight.W_600,
        color=AppColors.TEXT_PRIMARY,
    )
    
    H4 = TextStyle(
        size=18,
        weight=FontWeight.W_500,
        color=AppColors.TEXT_PRIMARY,
    )
    
    # Corps de texte
    BODY_LARGE = TextStyle(
        size=16,
        weight=FontWeight.NORMAL,
        color=AppColors.TEXT_PRIMARY,
    )
    
    BODY_MEDIUM = TextStyle(
        size=14,
        weight=FontWeight.NORMAL,
        color=AppColors.TEXT_PRIMARY,
    )
    
    BODY_SMALL = TextStyle(
        size=12,
        weight=FontWeight.NORMAL,
        color=AppColors.TEXT_SECONDARY,
    )
    
    # Textes spéciaux
    CAPTION = TextStyle(
        size=10,
        weight=FontWeight.NORMAL,
        color=AppColors.TEXT_SECONDARY,
    )
    
    BUTTON = TextStyle(
        size=14,
        weight=FontWeight.W_500,
        color=Colors.WHITE,
    )
    
    LABEL = TextStyle(
        size=12,
        weight=FontWeight.W_500,
        color=AppColors.TEXT_SECONDARY,
    )


# === ESPACEMENTS ===

class AppSpacing:
    """Espacements standard de l'application."""
    
    XS = 4
    SM = 8
    MD = 16
    LG = 24
    XL = 32
    XXL = 48


# === RAYONS DE BORDURE ===

class AppBorderRadius:
    """Rayons de bordure standard."""
    
    NONE = 0
    SM = 4
    MD = 8
    LG = 12
    XL = 16
    ROUND = 50


# === OMBRES ===

class AppShadows:
    """Ombres standard de l'application."""
    
    NONE = None
    
    SM = [
        BoxShadow(
            spread_radius=1,
            blur_radius=3,
            color=Colors.with_opacity(0.12, Colors.BLACK),
            offset=Offset(0, 1),
        )
    ]
    
    MD = [
        BoxShadow(
            spread_radius=2,
            blur_radius=6,
            color=Colors.with_opacity(0.16, Colors.BLACK),
            offset=Offset(0, 3),
        )
    ]
    
    LG = [
        BoxShadow(
            spread_radius=4,
            blur_radius=12,
            color=Colors.with_opacity(0.20, Colors.BLACK),
            offset=Offset(0, 6),
        )
    ]


# === THÈME PRINCIPAL ===

def get_app_theme() -> Theme:
    """Retourne le thème principal de l'application."""
    
    return Theme(
        color_scheme_seed=AppColors.PRIMARY,
        use_material3=True,
        
        # Couleurs
        primary_color=AppColors.PRIMARY,
        secondary_color=AppColors.SECONDARY,
        background_color=AppColors.BACKGROUND,
        scaffold_bg_color=AppColors.BACKGROUND,
        
        # Texte
        font_family="Roboto",
        
        # Thème de texte
        text_theme=TextTheme(
            display_large=AppTypography.H1,
            headline_large=AppTypography.H2,
            headline_medium=AppTypography.H3,
            title_large=AppTypography.H4,
            body_large=AppTypography.BODY_LARGE,
            body_medium=AppTypography.BODY_MEDIUM,
            body_small=AppTypography.BODY_SMALL,
            label_large=AppTypography.BUTTON,
            label_small=AppTypography.LABEL,
        ),
        
        # Input decoration
        input_decoration_theme=InputDecorationTheme(
            border_radius=BorderRadius.all(AppBorderRadius.MD),
            filled=True,
            fill_color=Colors.WHITE,
            content_padding=16,
        ),
        
        # Boutons
        elevated_button_theme=ElevatedButtonStyle(
            shape=BorderRadius.all(AppBorderRadius.MD),
            padding=16,
        ),
        
        # Cartes
        card_theme=CardTheme(
            elevation=2,
            shape=BorderRadius.all(AppBorderRadius.LG),
            shadow_color=Colors.with_opacity(0.1, Colors.BLACK),
        ),
        
        # AppBar
        appbar_theme=AppBarTheme(
            bgcolor=AppColors.PRIMARY,
            color=Colors.WHITE,
            elevation=0,
            center_title=True,
        ),
        
        # NavigationBar
        navigation_bar_theme=NavigationBarTheme(
            bgcolor=AppColors.SURFACE,
            indicator_color=Colors.with_opacity(0.1, AppColors.PRIMARY),
            label_behavior=NavigationBarLabelBehavior.ALWAYS_SHOW,
        ),
    )


# === COMPOSANTS RÉUTILISABLES ===

class AppComponents:
    """Composants UI réutilisables."""
    
    @staticmethod
    def stat_card(title: str, value: str, icon: str, color: str) -> ft.Card:
        """Crée une carte de statistique."""
        return ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(icon, size=40, color=color),
                        ft.Text(value, size=32, weight=FontWeight.BOLD, color=AppColors.TEXT_PRIMARY),
                        ft.Text(title, size=14, color=AppColors.TEXT_SECONDARY),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10,
                ),
                padding=AppSpacing.LG,
                width=200,
                height=150,
            ),
            elevation=3,
        )
    
    @staticmethod
    def status_badge(status: str) -> ft.Container:
        """Crée un badge de statut coloré."""
        colors = {
            'DISPONIBLE': AppColors.STATUS_DISPONIBLE,
            'RESERVE': AppColors.STATUS_RESERVE,
            'OCCUPE': AppColors.STATUS_OCCUPE,
            'NON_EXPLOITABLE': AppColors.STATUS_NON_EXPLOITABLE,
            'ACTIVE': AppColors.SUCCESS,
            'EXPIREE': AppColors.ERROR,
            'EN_ATTENTE': AppColors.WARNING,
            'PAYEE': AppColors.SUCCESS,
            'EMISE': AppColors.INFO,
        }
        
        color = colors.get(status, AppColors.TEXT_SECONDARY)
        
        return ft.Container(
            content=ft.Text(
                status.replace('_', ' ').title(),
                size=12,
                weight=FontWeight.W_500,
                color=Colors.WHITE,
            ),
            bgcolor=color,
            padding=ft.padding.symmetric(horizontal=12, vertical=4),
            border_radius=AppBorderRadius.ROUND,
        )
    
    @staticmethod
    def info_card(title: str, content: str, icon: str = None) -> ft.Card:
        """Crée une carte d'information."""
        return ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Icon(icon, size=24, color=AppColors.PRIMARY) if icon else None,
                                ft.Text(title, size=16, weight=FontWeight.BOLD),
                            ],
                            spacing=8,
                        ),
                        ft.Text(content, size=14, color=AppColors.TEXT_PRIMARY),
                    ],
                    spacing=8,
                ),
                padding=AppSpacing.MD,
            ),
            elevation=2,
        )
    
    @staticmethod
    def loading_indicator() -> ft.Container:
        """Crée un indicateur de chargement."""
        return ft.Container(
            content=ft.Column(
                [
                    ft.ProgressRing(),
                    ft.Text("Chargement...", size=14, color=AppColors.TEXT_SECONDARY),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=16,
            ),
            alignment=ft.alignment.center,
            padding=AppSpacing.XL,
        )
    
    @staticmethod
    def empty_state(message: str, icon: str = "info") -> ft.Container:
        """Crée un état vide (aucune donnée)."""
        return ft.Container(
            content=ft.Column(
                [
                    ft.Icon(icon, size=64, color=AppColors.TEXT_SECONDARY),
                    ft.Text(message, size=16, color=AppColors.TEXT_SECONDARY, text_align=ft.TextAlign.CENTER),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=16,
            ),
            alignment=ft.alignment.center,
            padding=AppSpacing.XXL,
        )
    
    @staticmethod
    def section_title(title: str, subtitle: str = None) -> ft.Column:
        """Crée un titre de section."""
        children = [
            ft.Text(title, size=20, weight=FontWeight.BOLD, color=AppColors.TEXT_PRIMARY),
        ]
        
        if subtitle:
            children.append(ft.Text(subtitle, size=14, color=AppColors.TEXT_SECONDARY))
        
        return ft.Column(
            children,
            spacing=4,
        )
    
    @staticmethod
    def divider() -> ft.Divider:
        """Crée un séparateur."""
        return ft.Divider(
            height=1,
            color=AppColors.DIVIDER,
            thickness=1,
        )
    
    @staticmethod
    def primary_button(text: str, on_click, icon: str = None) -> ft.ElevatedButton:
        """Crée un bouton principal."""
        return ft.ElevatedButton(
            text=text,
            icon=icon,
            on_click=on_click,
            bgcolor=AppColors.PRIMARY,
            color=Colors.WHITE,
            style=ft.ButtonStyle(
                shape=BorderRadius.all(AppBorderRadius.MD),
                padding=ft.padding.symmetric(horizontal=24, vertical=12),
            ),
        )
    
    @staticmethod
    def secondary_button(text: str, on_click, icon: str = None) -> ft.OutlinedButton:
        """Crée un bouton secondaire."""
        return ft.OutlinedButton(
            text=text,
            icon=icon,
            on_click=on_click,
            style=ft.ButtonStyle(
                color=AppColors.PRIMARY,
                shape=BorderRadius.all(AppBorderRadius.MD),
                padding=ft.padding.symmetric(horizontal=24, vertical=12),
                side={
                    "color": AppColors.PRIMARY,
                    "width": 1,
                },
            ),
        )
    
    @staticmethod
    def text_input(label: str, hint: str = None, icon: str = None, password: bool = False) -> ft.TextField:
        """Crée un champ de saisie standard."""
        return ft.TextField(
            label=label,
            hint_text=hint,
            prefix_icon=icon,
            password=password,
            can_reveal_password=password,
            border_radius=BorderRadius.all(AppBorderRadius.MD),
        )
    
    @staticmethod
    def caveau_marker(status: str, code: str) -> ft.Container:
        """Crée un marqueur de caveau pour la carte."""
        colors = {
            'DISPONIBLE': AppColors.STATUS_DISPONIBLE,
            'RESERVE': AppColors.STATUS_RESERVE,
            'OCCUPE': AppColors.STATUS_OCCUPE,
            'NON_EXPLOITABLE': AppColors.STATUS_NON_EXPLOITABLE,
        }
        
        color = colors.get(status, AppColors.TEXT_SECONDARY)
        
        return ft.Container(
            content=ft.Text(
                code,
                size=10,
                weight=FontWeight.BOLD,
                color=Colors.WHITE,
                text_align=ft.TextAlign.CENTER,
            ),
            width=40,
            height=40,
            bgcolor=color,
            border_radius=BorderRadius.all(AppBorderRadius.SM),
            alignment=ft.alignment.center,
            tooltip=f"{code} - {status}",
        )


# === UTILITAIRES ===

class AppUtils:
    """Utilitaires pour l'interface."""
    
    @staticmethod
    def format_montant(montant: float, devise: str = "FC") -> str:
        """Formate un montant avec la devise."""
        return f"{montant:,.2f} {devise}"
    
    @staticmethod
    def format_date(date_str: str) -> str:
        """Formate une date au format français."""
        try:
            from datetime import datetime
            date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return date.strftime("%d/%m/%Y")
        except:
            return date_str
    
    @staticmethod
    def format_datetime(datetime_str: str) -> str:
        """Formate une date et heure au format français."""
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            return dt.strftime("%d/%m/%Y %H:%M")
        except:
            return datetime_str
    
    @staticmethod
    def get_role_color(role: str) -> str:
        """Retourne la couleur associée à un rôle."""
        colors = {
            'ADMIN': AppColors.ROLE_ADMIN,
            'FIELD_AGENT': AppColors.ROLE_AGENT,
            'SECRETARY': AppColors.ROLE_SECRETARY,
            'CLIENT': AppColors.ROLE_CLIENT,
        }
        return colors.get(role, AppColors.TEXT_SECONDARY)
    
    @staticmethod
    def show_snackbar(page: ft.Page, message: str, type: str = "info"):
        """Affiche un snackbar (notification temporaire)."""
        colors = {
            'success': AppColors.SUCCESS,
            'error': AppColors.ERROR,
            'warning': AppColors.WARNING,
            'info': AppColors.INFO,
        }
        
        color = colors.get(type, AppColors.INFO)
        
        page.overlay.append(
            ft.SnackBar(
                content=ft.Text(message, color=Colors.WHITE),
                bgcolor=color,
                duration=3000,
            )
        )
        page.update()