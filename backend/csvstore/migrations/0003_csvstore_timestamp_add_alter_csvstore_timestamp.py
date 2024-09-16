# Generated by Django 5.1.1 on 2024-09-13 20:44

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('csvstore', '0002_alter_csvstore_amount_invested_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='csvstore',
            name='timestamp_add',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='csvstore',
            name='timestamp',
            field=models.DateTimeField(default=None),
        ),
    ]
