# Generated by Django 3.2.9 on 2021-11-15 15:23

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("common", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="member",
            name="status",
            field=models.CharField(default="PENDING", max_length=21),
        ),
    ]
