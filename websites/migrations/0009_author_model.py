from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('websites', '0008_remove_website_author_delete_author'),
    ]

    operations = [
        migrations.CreateModel(
            name='Author',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('logo', models.ImageField(upload_to='authors/', blank=True, null=True)),
                ('description', models.TextField(blank=True)),
                ('image', models.TextField(blank=True)),
                ('url', models.CharField(max_length=255, blank=True)),
            ],
        ),
        migrations.AddField(
            model_name='website',
            name='author',
            field=models.OneToOneField(on_delete=django.db.models.deletion.SET_NULL, null=True, blank=True, related_name='website', to='websites.author'),
        ),
    ] 