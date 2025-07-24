# Generated migration for transparency averages in ResearchField

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0002_add_broad_subject_term'),
    ]

    operations = [
        migrations.AddField(
            model_name='researchfield',
            name='avg_data_sharing',
            field=models.FloatField(default=0.0, help_text='Average percentage of papers with open data'),
        ),
        migrations.AddField(
            model_name='researchfield',
            name='avg_code_sharing',
            field=models.FloatField(default=0.0, help_text='Average percentage of papers with open code'),
        ),
        migrations.AddField(
            model_name='researchfield',
            name='avg_coi_disclosure',
            field=models.FloatField(default=0.0, help_text='Average percentage of papers with COI disclosure'),
        ),
        migrations.AddField(
            model_name='researchfield',
            name='avg_funding_disclosure',
            field=models.FloatField(default=0.0, help_text='Average percentage of papers with funding disclosure'),
        ),
        migrations.AddField(
            model_name='researchfield',
            name='avg_protocol_registration',
            field=models.FloatField(default=0.0, help_text='Average percentage of papers with protocol registration'),
        ),
        migrations.AddField(
            model_name='researchfield',
            name='avg_open_access',
            field=models.FloatField(default=0.0, help_text='Average percentage of papers with open access'),
        ),
    ] 