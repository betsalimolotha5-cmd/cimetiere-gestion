"""
Point d'entrée principal de l'application Flet.
"""
import flet as ft
from flet import Page, View, Theme, ThemeMode, Colors
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from frontend.api_client import api_client, APIError
from frontend.theme import get_app_theme, AppColors


class AppState:
    """État global de l'application."""
    
    def __init__(self):
        self.user = None
        self.token = None
        self.is_authenticated = False
        self.notifications_count = 0
        self.temp_user_id = None
        self.temp_user_email = None
    
    def set_user(self, user_data):
        self.user = user_data
        self.is_authenticated = True
    
    def clear_user(self):
        self.user = None
        self.token = None
        self.is_authenticated = False
        self.notifications_count = 0
        self.temp_user_id = None
        self.temp_user_email = None


app_state = AppState()


def main(page: Page):
    """Fonction principale de l'application Flet."""
    
    page.title = "Gestion Cimetière"
    page.theme_mode = ThemeMode.LIGHT
    page.padding = 0
    page.spacing = 0
    page.theme = get_app_theme()
    
    from frontend.pages import (
        LoginPage, MFAPage, DashboardPage, CartePage,
        ReservationsPage, ConcessionsPage, FacturesPage,
        NotificationsPage, ProfilePage, ReportsPage, ImportExportPage
    )
    
    pages = {
        '/login': LoginPage(page, app_state),
        '/mfa': MFAPage(page, app_state),
        '/dashboard': DashboardPage(page, app_state),
        '/carte': CartePage(page, app_state),
        '/reservations': ReservationsPage(page, app_state),
        '/concessions': ConcessionsPage(page, app_state),
        '/factures': FacturesPage(page, app_state),
        '/notifications': NotificationsPage(page, app_state),
        '/profile': ProfilePage(page, app_state),
        '/reports': ReportsPage(page, app_state),
        '/import-export': ImportExportPage(page, app_state),
    }
    
    def route_change(e):
        page.views.clear()
        route = page.route
        
        if route not in ['/login', '/mfa'] and not app_state.is_authenticated:
            page.route = "/login"
            page.update()
            return
        
        if route in pages:
            view = pages[route].build()
            page.views.append(view)
            if hasattr(pages[route], 'did_mount'):
                pages[route].did_mount()
        else:
            if app_state.is_authenticated:
                page.route = "/dashboard"
            else:
                page.route = "/login"
            page.update()
            return
        
        page.update()
    
    def view_pop(e):
        if len(page.views) > 1:
            page.views.pop()
            page.update()
    
    page.on_route_change = route_change
    page.on_view_pop = view_pop
    
    if app_state.is_authenticated:
        page.route = "/dashboard"
    else:
        page.route = "/login"
    
    page.go(page.route)


if __name__ == "__main__":
    ft.app(
        target=main,
        view=ft.AppView.WEB_BROWSER,
        host="0.0.0.0",
        port=8550,
    )