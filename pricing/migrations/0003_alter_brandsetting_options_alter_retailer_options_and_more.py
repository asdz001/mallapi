# Generated by Django 5.2.1 on 2025-05-16 06:34

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pricing', '0002_retailer_alter_brandsetting_retailer'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='brandsetting',
            options={'verbose_name': '브랜드정리', 'verbose_name_plural': '2. 브랜드정리'},
        ),
        migrations.AlterModelOptions(
            name='retailer',
            options={'verbose_name': '거래처처정리', 'verbose_name_plural': '1. 거래처정리'},
        ),
        migrations.CreateModel(
            name='CountrySetting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('country_input', models.CharField(max_length=100, verbose_name='수집된 국가 표기')),
                ('country_standard', models.CharField(max_length=100, verbose_name='표준 국가명')),
                ('fta_applicable', models.BooleanField(default=True, verbose_name='FTA 적용 여부')),
                ('retailer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='pricing.retailer', verbose_name='거래처')),
            ],
            options={
                'verbose_name': '원산지정리',
                'verbose_name_plural': '3. 원산지정리',
            },
        ),
    ]
