# Generated by Django 5.2.1 on 2025-05-15 03:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='retailer',
            field=models.CharField(default='UNKNOWN', max_length=100, verbose_name='거래처'),
            preserve_default=False,
        ),
    ]
