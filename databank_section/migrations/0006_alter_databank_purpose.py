# Generated by Django 5.1.6 on 2025-04-08 05:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('databank_section', '0005_remove_databank_photos_databankimage'),
    ]

    operations = [
        migrations.AlterField(
            model_name='databank',
            name='purpose',
            field=models.CharField(choices=[('For Selling a Property', 'for selling a property'), ('For Buying a Property', 'for buying a property'), ('For Rental or Lease', 'for rental or lease'), ('Looking to Rent or Lease a Property', 'looking to rent or lease')], max_length=50),
        ),
    ]
