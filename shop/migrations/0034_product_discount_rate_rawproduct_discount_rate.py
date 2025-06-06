# Generated by Django 5.2.1 on 2025-05-27 00:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0033_alter_product_external_product_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='discount_rate',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True, verbose_name='할인율 (%)'),
        ),
        migrations.AddField(
            model_name='rawproduct',
            name='discount_rate',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True, verbose_name='할인율 (%)'),
        ),
    ]
