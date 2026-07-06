"""
Composants UI réutilisables pour l'application Flet.
Centralise les éléments d'interface utilisés dans plusieurs pages.
"""
import flet as ft
from flet import (
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
    ElevatedButton,
    OutlinedButton,
    TextField,
    ProgressRing,
    border_radius,
    alignment,
    padding,
    CrossAxisAlignment,
    MainAxisAlignment,
)
from frontend.theme import AppColors, AppSpacing, AppBorderRadius


class StatCard:
    """Carte de statistique réutilisable."""
    
    @staticmethod
    def create(
        title: str,
        value: str,
        icon: str,
        color: str,
        width: int = 200,
        height: int = 150,
        on_click=None
    ) -> Card:
        """
        Crée une carte de statistique.
        
        Args:
            title: Titre de la statistique
            value: Valeur à afficher
            icon: Icône à afficher
            color: Couleur de l'icône
            width: Largeur de la carte
            height: Hauteur de la carte
            on_click: Fonction appelée au clic
        """
        return Card(
            content=Container(
                content=Column(
                    [
                        Icon(icon, size=40, color=color),
                        Text(
                            value,
                            size=28,
                            weight=FontWeight.BOLD,
                            color=AppColors.TEXT_PRIMARY,
                        ),
                        Text(
                            title,
                            size=13,
                            color=AppColors.TEXT_SECONDARY,
                            text_align=TextAlign.CENTER,
                        ),
                    ],
                    horizontal_alignment=CrossAxisAlignment.CENTER,
                    spacing=10,
                ),
                padding=AppSpacing.LG,
                width=width,
                height=height,
                border_radius=border_radius.all(AppBorderRadius.LG),
                alignment=alignment.center,
            ),
            elevation=3,
            on_click=on_click,
        )


class StatusBadge:
    """Badge de statut coloré."""
    
    # Couleurs des statuts
    STATUS_COLORS = {
        'DISPONIBLE': AppColors.STATUS_DISPONIBLE,
        'RESERVE': AppColors.STATUS_RESERVE,
        'OCCUPE': AppColors.STATUS_OCCUPE,
        'NON_EXPLOITABLE': AppColors.STATUS_NON_EXPLOITABLE,
        'ACTIVE': AppColors.SUCCESS,
        'EXPIREE': AppColors.ERROR,
        'RESILIEE': AppColors.TEXT_SECONDARY,
        'RENOUVELEE': Colors.BLUE,
        'EN_ATTENTE': AppColors.WARNING,
        'VALIDEE': Colors.BLUE,
        'REFUSEE': AppColors.ERROR,
        'REALISEE': AppColors.SUCCESS,
        'PAYEE': AppColors.SUCCESS,
        'EMISE': Colors.BLUE,
        'PARTIELLEMENT_PAYEE': Colors.ORANGE,
        'BROUILLON': AppColors.TEXT_SECONDARY,
        'ANNULEE': AppColors.TEXT_SECONDARY,
        'ENVOYE': AppColors.SUCCESS,
        'ECHEC': AppColors.ERROR,
    }
    
    @staticmethod
    def create(status: str, display_text: str = None) -> Container:
        """
        Crée un badge de statut.
        
        Args:
            status: Code du statut (ex: 'DISPONIBLE')
            display_text: Texte à afficher (par défaut: statut formaté)
        """
        if display_text is None:
            display_text = status.replace('_', ' ').title()
        
        color = StatusBadge.STATUS_COLORS.get(status, AppColors.TEXT_SECONDARY)
        
        return Container(
            content=Text(
                display_text,
                size=11,
                weight=FontWeight.BOLD,
                color=Colors.WHITE,
            ),
            bgcolor=color,
            padding=padding.symmetric(horizontal=12, vertical=5),
            border_radius=border_radius.all(AppBorderRadius.ROUND),
        )


class InfoCard:
    """Carte d'information avec icône et contenu."""
    
    @staticmethod
    def create(
        title: str,
        content: str,
        icon: str = None,
        color: str = None,
        on_click=None
    ) -> Card:
        """
        Crée une carte d'information.
        
        Args:
            title: Titre de la carte
            content: Contenu de la carte
            icon: Icône optionnelle
            color: Couleur de l'icône
            on_click: Fonction appelée au clic
        """
        icon_color = color or AppColors.PRIMARY
        
        header_controls = []
        if icon:
            header_controls.append(Icon(icon, size=24, color=icon_color))
        header_controls.append(
            Text(title, size=16, weight=FontWeight.BOLD, color=AppColors.TEXT_PRIMARY)
        )
        
        return Card(
            content=Container(
                content=Column(
                    [
                        Row(header_controls, spacing=8),
                        Text(
                            content,
                            size=14,
                            color=AppColors.TEXT_PRIMARY,
                        ),
                    ],
                    spacing=8,
                ),
                padding=AppSpacing.MD,
                border_radius=border_radius.all(AppBorderRadius.LG),
            ),
            elevation=2,
            on_click=on_click,
        )


class LoadingIndicator:
    """Indicateur de chargement."""
    
    @staticmethod
    def create(message: str = "Chargement...", visible: bool = True) -> Container:
        """
        Crée un indicateur de chargement.
        
        Args:
            message: Message à afficher
            visible: Visibilité initiale
        """
        return Container(
            content=Column(
                [
                    ProgressRing(),
                    Text(
                        message,
                        size=14,
                        color=AppColors.TEXT_SECONDARY,
                    ),
                ],
                horizontal_alignment=CrossAxisAlignment.CENTER,
                spacing=16,
            ),
            alignment=alignment.center,
            padding=AppSpacing.XL,
            visible=visible,
        )


class EmptyState:
    """État vide (aucune donnée)."""
    
    @staticmethod
    def create(
        message: str,
        icon: str = Icons.INFO_OUTLINE,
        action_text: str = None,
        on_action=None
    ) -> Container:
        """
        Crée un état vide.
        
        Args:
            message: Message à afficher
            icon: Icône à afficher
            action_text: Texte du bouton d'action optionnel
            on_action: Fonction appelée au clic sur le bouton
        """
        controls = [
            Icon(icon, size=64, color=AppColors.TEXT_SECONDARY),
            Text(
                message,
                size=16,
                color=AppColors.TEXT_SECONDARY,
                text_align=TextAlign.CENTER,
            ),
        ]
        
        if action_text and on_action:
            controls.append(
                ElevatedButton(
                    action_text,
                    on_click=on_action,
                    bgcolor=AppColors.PRIMARY,
                    color=Colors.WHITE,
                )
            )
        
        return Container(
            content=Column(
                controls,
                horizontal_alignment=CrossAxisAlignment.CENTER,
                spacing=16,
            ),
            alignment=alignment.center,
            padding=AppSpacing.XXL,
        )


class SectionTitle:
    """Titre de section."""
    
    @staticmethod
    def create(title: str, subtitle: str = None, icon: str = None) -> Column:
        """
        Crée un titre de section.
        
        Args:
            title: Titre principal
            subtitle: Sous-titre optionnel
            icon: Icône optionnelle
        """
        title_controls = []
        
        if icon:
            title_controls.append(Icon(icon, size=24, color=AppColors.PRIMARY))
        
        title_controls.append(
            Text(
                title,
                size=20,
                weight=FontWeight.BOLD,
                color=AppColors.TEXT_PRIMARY,
            )
        )
        
        controls = [
            Row(title_controls, spacing=10),
        ]
        
        if subtitle:
            controls.append(
                Text(
                    subtitle,
                    size=14,
                    color=AppColors.TEXT_SECONDARY,
                )
            )
        
        return Column(
            controls,
            spacing=4,
        )


class PrimaryButton:
    """Bouton principal."""
    
    @staticmethod
    def create(
        text: str,
        on_click,
        icon: str = None,
        width: int = None,
        disabled: bool = False
    ) -> ElevatedButton:
        """
        Crée un bouton principal.
        
        Args:
            text: Texte du bouton
            on_click: Fonction appelée au clic
            icon: Icône optionnelle
            width: Largeur optionnelle
            disabled: État désactivé
        """
        return ElevatedButton(
            text=text,
            icon=icon,
            on_click=on_click,
            bgcolor=AppColors.PRIMARY,
            color=Colors.WHITE,
            width=width,
            disabled=disabled,
            style=ft.ButtonStyle(
                shape=border_radius.all(AppBorderRadius.MD),
                padding=padding.symmetric(horizontal=24, vertical=12),
            ),
        )


class SecondaryButton:
    """Bouton secondaire."""
    
    @staticmethod
    def create(
        text: str,
        on_click,
        icon: str = None,
        width: int = None,
        disabled: bool = False
    ) -> OutlinedButton:
        """
        Crée un bouton secondaire.
        
        Args:
            text: Texte du bouton
            on_click: Fonction appelée au clic
            icon: Icône optionnelle
            width: Largeur optionnelle
            disabled: État désactivé
        """
        return OutlinedButton(
            text=text,
            icon=icon,
            on_click=on_click,
            width=width,
            disabled=disabled,
            style=ft.ButtonStyle(
                color=AppColors.PRIMARY,
                shape=border_radius.all(AppBorderRadius.MD),
                padding=padding.symmetric(horizontal=24, vertical=12),
                side={
                    "color": AppColors.PRIMARY,
                    "width": 1,
                },
            ),
        )


class TextInput:
    """Champ de saisie standardisé."""
    
    @staticmethod
    def create(
        label: str,
        hint: str = None,
        icon: str = None,
        password: bool = False,
        multiline: bool = False,
        disabled: bool = False,
        value: str = None,
        on_change=None,
        on_submit=None,
        width: int = None,
        max_length: int = None,
    ) -> TextField:
        """
        Crée un champ de saisie standardisé.
        
        Args:
            label: Label du champ
            hint: Texte d'aide
            icon: Icône optionnelle
            password: Champ mot de passe
            multiline: Champ multiligne
            disabled: État désactivé
            value: Valeur initiale
            on_change: Fonction appelée au changement
            on_submit: Fonction appelée à la soumission
            width: Largeur optionnelle
            max_length: Longueur maximale
        """
        return TextField(
            label=label,
            hint_text=hint,
            prefix_icon=icon,
            password=password,
            can_reveal_password=password,
            multiline=multiline,
            min_lines=2 if multiline else 1,
            max_lines=4 if multiline else 1,
            disabled=disabled,
            value=value,
            on_change=on_change,
            on_submit=on_submit,
            width=width,
            max_length=max_length,
            border_radius=border_radius.all(AppBorderRadius.MD),
        )


class CaveauMarker:
    """Marqueur visuel d'un caveau pour la carte."""
    
    @staticmethod
    def create(
        code: str,
        status: str,
        type_caveau: str = None,
        on_click=None,
        width: int = 100,
        height: int = 80,
    ) -> Container:
        """
        Crée un marqueur de caveau.
        
        Args:
            code: Code du caveau
            status: Statut du caveau
            type_caveau: Type de caveau
            on_click: Fonction appelée au clic
            width: Largeur du marqueur
            height: Hauteur du marqueur
        """
        color = StatusBadge.STATUS_COLORS.get(status, AppColors.TEXT_SECONDARY)
        
        content_controls = [
            Text(
                code,
                size=13,
                weight=FontWeight.BOLD,
                color=Colors.WHITE,
                text_align=TextAlign.CENTER,
            ),
        ]
        
        if type_caveau:
            content_controls.append(
                Text(
                    type_caveau.replace('_', ' ').title(),
                    size=9,
                    color=Colors.with_opacity(0.8, Colors.WHITE),
                    text_align=TextAlign.CENTER,
                )
            )
        
        return Container(
            content=Column(
                content_controls,
                horizontal_alignment=CrossAxisAlignment.CENTER,
                spacing=4,
            ),
            width=width,
            height=height,
            bgcolor=color,
            border_radius=border_radius.all(AppBorderRadius.MD),
            alignment=alignment.center,
            on_click=on_click,
            tooltip=f"{code} - {status.replace('_', ' ').title()}",
            ink=True,
            animate_opacity=ft.Animation(300, ft.AnimationCurve.EASE_IN_OUT),
        )


class DetailRow:
    """Ligne de détail label/valeur."""
    
    @staticmethod
    def create(
        label: str,
        value: str,
        highlight: bool = False,
        label_width: int = 150
    ) -> Row:
        """
        Crée une ligne de détail.
        
        Args:
            label: Label
            value: Valeur
            highlight: Mettre en évidence la valeur
            label_width: Largeur du label
        """
        return Row(
            [
                Text(
                    f"{label} :",
                    size=13,
                    color=AppColors.TEXT_SECONDARY,
                    width=label_width,
                ),
                Text(
                    value,
                    size=13,
                    weight=FontWeight.BOLD if highlight else FontWeight.W_500,
                    color=Colors.RED if highlight else AppColors.TEXT_PRIMARY,
                ),
            ],
            spacing=10,
        )


class ConfirmationDialog:
    """Boîte de dialogue de confirmation."""
    
    @staticmethod
    def create(
        title: str,
        message: str,
        on_confirm,
        on_cancel=None,
        confirm_text: str = "Confirmer",
        cancel_text: str = "Annuler",
        confirm_color: str = AppColors.PRIMARY,
    ) -> ft.AlertDialog:
        """
        Crée une boîte de dialogue de confirmation.
        
        Args:
            title: Titre de la boîte
            message: Message à afficher
            on_confirm: Fonction appelée à la confirmation
            on_cancel: Fonction appelée à l'annulation
            confirm_text: Texte du bouton de confirmation
            cancel_text: Texte du bouton d'annulation
            confirm_color: Couleur du bouton de confirmation
        """
        def close_dialog(e):
            if hasattr(e, 'page'):
                e.page.close(dialog)
            else:
                # Fallback pour les anciennes versions
                pass
        
        dialog = ft.AlertDialog(
            title=Text(title),
            content=Text(message),
            actions=[
                ft.TextButton(
                    cancel_text,
                    on_click=lambda e: (on_cancel(e) if on_cancel else close_dialog(e)),
                ),
                ElevatedButton(
                    confirm_text,
                    bgcolor=confirm_color,
                    color=Colors.WHITE,
                    on_click=on_confirm,
                ),
            ],
        )
        
        return dialog


class MessageDialog:
    """Boîte de dialogue de message simple."""
    
    @staticmethod
    def create(
        title: str,
        message: str,
        on_close=None,
        icon: str = Icons.INFO,
        icon_color: str = AppColors.PRIMARY,
    ) -> ft.AlertDialog:
        """
        Crée une boîte de dialogue de message.
        
        Args:
            title: Titre de la boîte
            message: Message à afficher
            on_close: Fonction appelée à la fermeture
            icon: Icône à afficher
            icon_color: Couleur de l'icône
        """
        dialog = ft.AlertDialog(
            title=Row(
                [
                    Icon(icon, color=icon_color, size=28),
                    Text(title),
                ],
                spacing=10,
            ),
            content=Text(message),
            actions=[
                ft.TextButton(
                    "OK",
                    on_click=lambda e: (
                        on_close(e) if on_close else 
                        (e.page.close(dialog) if hasattr(e, 'page') else None)
                    ),
                ),
            ],
        )
        
        return dialog