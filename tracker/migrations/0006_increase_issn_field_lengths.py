# Generated migration to fix ISSN field length issue

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0005_alter_paper_options_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='journal',
            name='issn_electronic',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AlterField(
            model_name='journal',
            name='issn_print',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AlterField(
            model_name='journal',
            name='issn_linking',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
    ] 