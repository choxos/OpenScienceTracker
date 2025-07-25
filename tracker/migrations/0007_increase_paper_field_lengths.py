# Generated migration to increase Paper field lengths

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0006_increase_issn_field_lengths'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paper',
            name='source',
            field=models.CharField(help_text='Data source (e.g., PMC, MED)', max_length=50),
        ),
        migrations.AlterField(
            model_name='paper',
            name='pmcid',
            field=models.CharField(blank=True, db_index=True, help_text='PubMed Central ID', max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='paper',
            name='pmid',
            field=models.CharField(blank=True, db_index=True, help_text='PubMed ID', max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='paper',
            name='journal_issn',
            field=models.CharField(blank=True, help_text='Journal ISSN', max_length=50, null=True),
        ),
    ] 