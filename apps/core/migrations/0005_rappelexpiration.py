# Generated migration for RappelExpiration model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_auditlogentry'),
    ]

    operations = [
        migrations.CreateModel(
            name='RappelExpiration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type_rappel', models.CharField(choices=[('J30', '30 jours avant'), ('J15', '15 jours avant'), ('J7', '7 jours avant'), ('J0', 'Jour J (Expiré)')], max_length=10, verbose_name='Type de rappel')),
                ('date_envoi', models.DateTimeField(auto_now_add=True, verbose_name="Date d'envoi")),
                ('statut_envoi', models.CharField(choices=[('SUCCES', 'Succès'), ('ECHEC', 'Échec')], default='SUCCES', max_length=20, verbose_name="Statut de l'envoi")),
                ('message_erreur', models.TextField(blank=True, verbose_name="Message d'erreur (si échec)")),
                ('concession', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rappels_expiration', to='core.concession', verbose_name='Concession concernée')),
            ],
            options={
                'verbose_name': "Rappel d'expiration",
                'verbose_name_plural': "Rappels d'expiration",
                'ordering': ['-date_envoi'],
            },
        ),
        migrations.AddConstraint(
            model_name='rappelexpiration',
            constraint=models.UniqueConstraint(fields=('concession', 'type_rappel'), name='unique_rappel_par_concession'),
        ),
    ]