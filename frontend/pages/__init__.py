"""
Pages de l'application Flet.
"""
from .login_page import LoginPage
from .mfa_page import MFAPage
from .dashboard_page import DashboardPage
from .carte_page import CartePage
from .reservations_page import ReservationsPage
from .concessions_page import ConcessionsPage
from .factures_page import FacturesPage
from .notifications_page import NotificationsPage
from .profile_page import ProfilePage
from .reports_page import ReportsPage
from .import_export_page import ImportExportPage

__all__ = [
    'LoginPage',
    'MFAPage',
    'DashboardPage',
    'CartePage',
    'ReservationsPage',
    'ConcessionsPage',
    'FacturesPage',
    'NotificationsPage',
    'ProfilePage',
    'ReportsPage',
    'ImportExportPage',
]