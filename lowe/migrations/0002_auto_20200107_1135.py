# Generated by Django 2.1.5 on 2020-01-07 03:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lowe', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='lowe',
            name='e_date',
        ),
        migrations.RemoveField(
            model_name='lowe',
            name='s_date',
        ),
        migrations.AlterField(
            model_name='lowe',
            name='paid',
            field=models.BooleanField(default=False, verbose_name='是否付押金'),
        ),
    ]
