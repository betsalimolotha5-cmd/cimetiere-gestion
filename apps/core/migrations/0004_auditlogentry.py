# Generated manually — modèle AuditLogEntry (journal d'audit immuable, CDC section 4)

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0003_alter_caveau_type_caveau_delete_exhumation'),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditLogEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('horodatage', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Date et heure')),
                ('niveau', models.CharField(choices=[('INFO', 'Information'), ('WARNING', 'Avertissement'), ('ERROR', 'Erreur')], default='INFO', max_length=10, verbose_name='Niveau')),
                ('action', models.CharField(db_index=True, help_text="Code d'action, ex: CAVEAU_RESERVED, CAVEAU_STATUS_CHANGED, FACTURE_CREATED", max_length=100, verbose_name='Action')),
                ('module', models.CharField(blank=True, help_text="Fichier/module d'origine du log.", max_length=100, verbose_name='Module')),
                ('message', models.TextField(help_text='Message complet du log (contexte, identifiants concernés, etc.)', verbose_name='Détail')),
                ('utilisateur', models.ForeignKey(blank=True, help_text="Utilisateur authentifié à l'origine de l'action (si disponible).", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='entrees_audit', to=settings.AUTH_USER_MODEL, verbose_name='Utilisateur')),
            ],
            options={
                'verbose_name': "Entrée d'audit",
                'verbose_name_plural': "Journal d'audit",
                'ordering': ['-horodatage'],
            },
        ),
    ]
