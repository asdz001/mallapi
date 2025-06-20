# Generated by Django 5.2.1 on 2025-06-18 08:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dictionary', '0005_alter_categorylevel1_options_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='categorylevel1',
            options={'verbose_name': '성별', 'verbose_name_plural': '1. 성별'},
        ),
        migrations.AlterModelOptions(
            name='categorylevel2',
            options={'verbose_name': '대분류', 'verbose_name_plural': '2. 대분류'},
        ),
        migrations.AlterModelOptions(
            name='categorylevel3',
            options={'verbose_name': '중분류', 'verbose_name_plural': '3. 중분류'},
        ),
        migrations.AlterModelOptions(
            name='categorylevel4',
            options={'verbose_name': '소분류', 'verbose_name_plural': '4. 소분류'},
        ),
        migrations.AlterField(
            model_name='categorylevel1',
            name='name',
            field=models.CharField(max_length=100, unique=True, verbose_name='표준 성별'),
        ),
        migrations.AlterField(
            model_name='categorylevel1alias',
            name='alias',
            field=models.CharField(max_length=100, unique=True, verbose_name='치환 성별'),
        ),
        migrations.AlterField(
            model_name='categorylevel2',
            name='name',
            field=models.CharField(max_length=100, unique=True, verbose_name='표준 대분류'),
        ),
        migrations.AlterField(
            model_name='categorylevel2alias',
            name='alias',
            field=models.CharField(max_length=100, unique=True, verbose_name='치환 대분류'),
        ),
        migrations.AlterField(
            model_name='categorylevel3',
            name='name',
            field=models.CharField(max_length=100, unique=True, verbose_name='표준 중분류'),
        ),
        migrations.AlterField(
            model_name='categorylevel3alias',
            name='alias',
            field=models.CharField(max_length=100, unique=True, verbose_name='치환 중분류'),
        ),
        migrations.AlterField(
            model_name='categorylevel4',
            name='name',
            field=models.CharField(max_length=100, unique=True, verbose_name='표준 소분류'),
        ),
        migrations.AlterField(
            model_name='categorylevel4alias',
            name='alias',
            field=models.CharField(max_length=100, unique=True, verbose_name='치환 소분류'),
        ),
    ]
