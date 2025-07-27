import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'site_creator.settings')
django.setup()

from websites.models import Page
from collections import defaultdict

# Map: (website_id, slug) -> list of pages
slug_map = defaultdict(list)
for page in Page.objects.all():
    slug_map[(page.website_id, page.slug)].append(page)

for (website_id, slug), pages in slug_map.items():
    if len(pages) > 1:
        print(f"Duplicate slug: '{slug}' in website_id={website_id} (count: {len(pages)})")
        for i, page in enumerate(pages):
            if i == 0:
                continue  # Keep the first occurrence as is
            new_slug = f"{slug}-{i+1}"
            print(f"Renaming page id={page.id} from '{slug}' to '{new_slug}' (website_id={website_id})")
            page.slug = new_slug
            page.save()

print("Duplicate slugs per website fixed.") 