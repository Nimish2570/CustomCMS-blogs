from django.db import migrations, models
import django.utils.timezone

def set_dates(apps, schema_editor):
    Page = apps.get_model('websites', 'Page')
    for page in Page.objects.all():
        if not page.date_published:
            page.date_published = page.created_at
        if not page.date_modified:
            page.date_modified = page.updated_at
        page.save()

class Migration(migrations.Migration):
    dependencies = [
        ('websites', '0003_website_contact_box_color_website_header_box_color_and_more'),
    ]
    operations = [
        migrations.AddField(
            model_name='page',
            name='date_published',
            field=models.DateTimeField(null=True, blank=True, help_text='Date when the page was published'),
        ),
        migrations.AddField(
            model_name='page',
            name='date_modified',
            field=models.DateTimeField(null=True, blank=True, help_text='Date when the page was last modified'),
        ),
        migrations.RunPython(set_dates, reverse_code=migrations.RunPython.noop),
    ] 