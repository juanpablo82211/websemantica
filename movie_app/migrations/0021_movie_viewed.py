# Generated by Django 5.0.1 on 2024-12-03 13:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('movie_app', '0020_remove_profile_website_alter_profile_instagram_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='movie',
            name='viewed',
            field=models.BooleanField(blank=True, null=True),
        ),
    ]
