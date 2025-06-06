# Generated by Django 5.2.1 on 2025-05-20 04:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pricing', '0012_alter_brandsetting_retailer'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='retailer',
            options={'verbose_name': '거래처', 'verbose_name_plural': '1. 거래처'},
        ),
        migrations.AddField(
            model_name='retailer',
            name='code',
            field=models.CharField(default=1, max_length=50, unique=True, verbose_name='업체코드'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='retailer',
            name='name',
            field=models.CharField(max_length=100, verbose_name='업체명'),
        ),
    ]
