# Generated by Django 5.2.1 on 2025-05-20 02:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0013_alter_cart_options_alter_cartoption_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='calculated_price_krw',
            field=models.DecimalField(blank=True, decimal_places=0, max_digits=12, null=True, verbose_name='원화가'),
        ),
    ]
