# Generated by Django 5.2.1 on 2025-05-16 04:38

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0002_product_retailer'),
    ]

    operations = [
        migrations.RenameField(
            model_name='product',
            old_name='name',
            new_name='product_name',
        ),
        migrations.RemoveField(
            model_name='product',
            name='brand',
        ),
        migrations.RemoveField(
            model_name='product',
            name='price',
        ),
        migrations.RemoveField(
            model_name='product',
            name='stock',
        ),
        migrations.AddField(
            model_name='product',
            name='brand_name',
            field=models.CharField(default=1, max_length=100, verbose_name='브랜드명'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='product',
            name='category1',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='카테고리1'),
        ),
        migrations.AddField(
            model_name='product',
            name='category2',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='카테고리2'),
        ),
        migrations.AddField(
            model_name='product',
            name='color',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='색상명'),
        ),
        migrations.AddField(
            model_name='product',
            name='gender',
            field=models.CharField(blank=True, max_length=10, null=True, verbose_name='성별'),
        ),
        migrations.AddField(
            model_name='product',
            name='image_url',
            field=models.URLField(blank=True, null=True, verbose_name='이미지 URL'),
        ),
        migrations.AddField(
            model_name='product',
            name='material',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='소재'),
        ),
        migrations.AddField(
            model_name='product',
            name='origin',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='원산지'),
        ),
        migrations.AddField(
            model_name='product',
            name='price_org',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='원가'),
        ),
        migrations.AddField(
            model_name='product',
            name='price_retail',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='소비자가'),
        ),
        migrations.AddField(
            model_name='product',
            name='price_supply',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='공급가'),
        ),
        migrations.AddField(
            model_name='product',
            name='season',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='시즌'),
        ),
        migrations.AddField(
            model_name='product',
            name='sku',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='SKU'),
        ),
        migrations.AddField(
            model_name='product',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='수정일'),
        ),
        migrations.AlterField(
            model_name='product',
            name='retailer',
            field=models.CharField(max_length=100, verbose_name='부티크명'),
        ),
        migrations.CreateModel(
            name='Cart',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.IntegerField(default=1)),
                ('added_at', models.DateTimeField(auto_now_add=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='shop.product')),
            ],
        ),
    ]
