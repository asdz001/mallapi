# Generated by Django 5.2.1 on 2025-05-16 06:44

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pricing', '0003_alter_brandsetting_options_alter_retailer_options_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='FixedCountry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='표준 국가명')),
                ('fta_applicable', models.BooleanField(default=True, verbose_name='FTA 적용 여부')),
            ],
        ),
        migrations.RemoveField(
            model_name='countrysetting',
            name='country_standard',
        ),
        migrations.RemoveField(
            model_name='countrysetting',
            name='fta_applicable',
        ),
        migrations.AddField(
            model_name='countrysetting',
            name='standard_country',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='pricing.fixedcountry', verbose_name='표준 국가명'),
        ),
    ]
