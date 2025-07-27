from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.core.files.storage import default_storage
from django.conf import settings
import os
import zipfile
from github import Github
from .models import Website, Page
from .forms import WebsiteForm, PageForm, GitHubRepoForm, MenuForm, WebsiteSettingsForm, TrackingSettingsForm, FormSettingsForm, AuthorForm
import tempfile
import shutil
from datetime import datetime
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
from PIL import Image
import uuid
import git
from django.forms import modelform_factory
import markdown
import cloudinary.uploader
import requests
import json
import time
from bs4 import BeautifulSoup
from urllib.parse import unquote
import re
from django.utils import timezone
from .models import Author

@login_required
def dashboard(request):
    websites = Website.objects.filter(owner=request.user)
    return render(request, 'websites/dashboard.html', {'websites': websites})

@login_required
def create_website(request):
    if request.method == 'POST':
        form = WebsiteForm(request.POST, request.FILES)
        if form.is_valid():
            website = form.save(commit=False)
            website.owner = request.user
            # Set default values for removed fields
            website.name = website.domain  # or set to a default value
            website.phone_number_display = ''
            website.robots_txt = ''
            website.github_repo = ''
            website.is_public_repo = False
            website.save()
            # Create homepage
            Page.objects.create(
                website=website,
                title='Home',
                content='Welcome to our website!',
                slug='home',
                is_homepage=True
            )
            messages.success(request, 'Website created successfully!')
            return redirect('dashboard')
    else:
        form = WebsiteForm()
    return render(request, 'websites/create_website.html', {'form': form})

@login_required
def edit_website(request, website_id):
    website = get_object_or_404(Website, id=website_id, owner=request.user)
    
    if request.method == 'POST':
        form = WebsiteForm(request.POST, request.FILES, instance=website)
        if form.is_valid():
            form.save()
            messages.success(request, 'Website updated successfully!')
            return redirect('dashboard')
    else:
        form = WebsiteForm(instance=website)
    return render(request, 'websites/edit_website.html', {'form': form, 'website': website})

@login_required
def manage_pages(request, website_id):
    website = get_object_or_404(Website, id=website_id, owner=request.user)
    pages = website.pages.all()
    nofollow_urls = [f'/{p.slug}' for p in website.pages.filter(nofollow_document=True)]
    return render(request, 'websites/manage_pages.html', {'website': website, 'pages': pages, 'nofollow_urls': nofollow_urls})

@login_required
def create_page(request, website_id):
    website = get_object_or_404(Website, id=website_id, owner=request.user)
    
    if request.method == 'POST':
        form = PageForm(request.POST)
        if form.is_valid():
            page = form.save(commit=False)
            page.website = website
            
            # If this is set as homepage, unset any existing homepage
            if page.is_homepage:
                website.pages.filter(is_homepage=True).update(is_homepage=False)
            
            # Generate slug if not provided
            if not page.slug:
                base_slug = slugify(page.title)
                slug = base_slug
                counter = 1
                while Page.objects.filter(slug=slug).exists():
                    slug = f"{base_slug}-{counter}"
                    counter += 1
                page.slug = slug
            
            # Set date_published and date_modified if not provided
            if not page.date_published:
                page.date_published = timezone.now()
            if not page.date_modified:
                page.date_modified = timezone.now()
            
            page.save()
            messages.success(request, 'Page created successfully!')
            return redirect('manage_pages', website_id=website.id)
    else:
        form = PageForm()
    nofollow_urls = [f'/{p.slug}' for p in website.pages.filter(nofollow_document=True)]
    return render(request, 'websites/create_page.html', {'form': form, 'website': website, 'nofollow_urls': nofollow_urls})

@login_required
def edit_page(request, website_id, page_id):
    website = get_object_or_404(Website, id=website_id, owner=request.user)
    page = get_object_or_404(Page, id=page_id, website=website)
    
    if request.method == 'POST':
        form = PageForm(request.POST, instance=page)
        if form.is_valid():
            # If this is set as homepage, unset any existing homepage
            if form.cleaned_data['is_homepage'] and not page.is_homepage:
                website.pages.filter(is_homepage=True).update(is_homepage=False)
            
            # Generate slug if not provided
            if not form.cleaned_data['slug']:
                base_slug = slugify(form.cleaned_data['title'])
                slug = base_slug
                counter = 1
                while Page.objects.filter(slug=slug).exists():
                    slug = f"{base_slug}-{counter}"
                    counter += 1
                form.cleaned_data['slug'] = slug
            
            # Set date_published and date_modified if not provided
            instance = form.save(commit=False)
            if not instance.date_published:
                instance.date_published = instance.created_at or timezone.now()
            instance.date_modified = timezone.now()
            instance.save()
            
            messages.success(request, 'Page updated successfully!')
            return redirect('manage_pages', website_id=website.id)
    else:
        form = PageForm(instance=page)
    nofollow_urls = [f'/{p.slug}' for p in website.pages.filter(nofollow_document=True)]
    return render(request, 'websites/edit_page.html', {'form': form, 'website': website, 'page': page, 'nofollow_urls': nofollow_urls})

@csrf_exempt
def ckeditor_upload_image(request):
    print("CKEditor upload request received")
    if request.method == 'POST' and request.FILES.get('upload'):
        upload_file = request.FILES['upload']

        # Allowed image types
        allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'avif']
        allowed_mimetypes = [
            'image/jpeg', 'image/png', 'image/gif', 'image/bmp',
            'image/webp', 'image/avif'
        ]

        # Extract file extension
        ext = os.path.splitext(upload_file.name)[1].lower().replace('.', '')
        if ext not in allowed_extensions or upload_file.content_type not in allowed_mimetypes:
            return JsonResponse({'uploaded': 0, 'error': {'message': 'File type not supported.'}})

        # Prepare metadata
        orig_name, _ = os.path.splitext(upload_file.name)  # e.g., 'what_is_knee_pain'
        print(f"Original filename: {orig_name}")
        alt_text = " ".join(word.capitalize() for word in orig_name.split("_"))  # e.g., 'What Is Knee Pain'

        website_id = request.POST.get('website_id', '1')
        page_id = request.POST.get('page_id', '1')
        unique_hash = uuid.uuid4().hex

        # Construct public_id with filename in parentheses
        public_id = f"website_{website_id}_page_{page_id}_({orig_name})_{unique_hash}"
        print(f"Public ID for upload: {public_id}")

        try:
            # Upload to Cloudinary with format to preserve extension
            result = cloudinary.uploader.upload(
                upload_file,
                public_id=public_id,
                resource_type="image",
                format=ext  # Ensures proper extension in storage
            )

            file_url = result['secure_url']
            file_name = f"{public_id}.{ext}"  # Final stored filename with extension

            return JsonResponse({
                'uploaded': 1,
                'fileName': file_name,
                'url': file_url,
                'alt': alt_text,
            })

        except Exception as e:
            return JsonResponse({'uploaded': 0, 'error': {'message': f'Upload failed: {str(e)}'}})

    return JsonResponse({'uploaded': 0, 'error': {'message': 'Error uploading file.'}})

@login_required
def export_website(request, website_id):
    website = get_object_or_404(Website, id=website_id)
    # Get header and footer menu content from Menu model
    header_menu = website.menus.filter(type='header').first()
    footer_menu = website.menus.filter(type='footer').first()
    header_menu_content = header_menu.content if header_menu else ''
    footer_menu_content = footer_menu.content if footer_menu else ''

    def parse_menu_markdown(md):
        # Returns a dict: {'paragraphs': [...], 'links': [menu structure]}
        lines = md.splitlines()
        stack = []
        root = []
        paragraphs = []
        for line in lines:
            if not line.strip():
                continue
            depth = 0
            orig_line = line
            while line.startswith('\t'):
                depth += 1
                line = line[1:]
            import re
            m = re.match(r'\[(.*?)\]\((.*?)\)', line.strip())
            if m:
                title, url = m.groups()
                # Normalize URL: if not empty and not external, ensure starts with '/'
                if url and not url.startswith(('http://', 'https://', '/')):
                    url = '/' + url.lstrip('/')
                node = {'title': title, 'url': url, 'children': []}
                if depth == 0:
                    root.append(node)
                    stack = [node]
                else:
                    if len(stack) >= depth:
                        stack = stack[:depth]
                    if stack:
                        stack[-1]['children'].append(node)
                    stack.append(node)
            else:
                # Not a link, treat as paragraph
                if depth == 0:
                    paragraphs.append(orig_line.strip())
        return {'paragraphs': paragraphs, 'links': root}

    header_menu_parsed = parse_menu_markdown(header_menu_content)
    footer_menu_parsed = parse_menu_markdown(footer_menu_content)

    # Create a temporary directory for the static site
    with tempfile.TemporaryDirectory() as temp_dir:
        static_site_dir = os.path.join(temp_dir, 'static_site')
        static_dir = os.path.join(temp_dir, 'static')
        staticfiles_dir = os.path.join(temp_dir, 'staticfiles')
        media_dir = os.path.join(temp_dir, 'media')
        templates_dir = os.path.join(temp_dir, 'templates')
        
        # Create directories
        os.makedirs(static_site_dir, exist_ok=True)
        os.makedirs(static_dir, exist_ok=True)
        os.makedirs(staticfiles_dir, exist_ok=True)
        os.makedirs(media_dir, exist_ok=True)
        os.makedirs(templates_dir, exist_ok=True)
        
        # Copy static files
        static_files = [
            'css/bootstrap.min.css',
            'js/bootstrap.bundle.min.js',
        ]
        
        for static_file in static_files:
            src_path = os.path.join(settings.STATIC_ROOT, static_file)
            if os.path.exists(src_path):
                dest_path = os.path.join(static_dir, static_file)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.copy2(src_path, dest_path)
        
        # Copy templates
        template_files = [
            'static_base.html',
            'static_page.html',
            '404.html',
            'sitemap.xml',
        ]
        
        for template_file in template_files:
            src_path = os.path.join(settings.BASE_DIR, 'templates', 'websites', template_file)
            if os.path.exists(src_path):
                dest_path = os.path.join(templates_dir, template_file)
                shutil.copy2(src_path, dest_path)
        
        # Copy the static top image for all websites
        top_image_dest_dir = os.path.join(media_dir, 'websites')
        os.makedirs(top_image_dest_dir, exist_ok=True)
        def get_file_local_path_or_download(field, dest_path):
            """
            If the file is stored locally, return its path.
            If stored in cloud (no .path), download from .url to dest_path and return dest_path.
            """
            if field:
                try:
                    file_path = field.path
                    if os.path.exists(file_path):
                        return file_path
                except NotImplementedError:
                    # Cloud storage: download
                    url = field.url
                    r = requests.get(url, stream=True)
                    if r.status_code == 200:
                        with open(dest_path, 'wb') as f:
                            for chunk in r.iter_content(1024):
                                f.write(chunk)
                        return dest_path
            return None
        # Handle heading background image
        top_image_dest = os.path.join(top_image_dest_dir, 'title-background.jpg')
        heading_img_field = website.heading_background_image
        heading_img_path = get_file_local_path_or_download(heading_img_field, top_image_dest)
        if heading_img_path:
            try:
                img = Image.open(heading_img_path)
                rgb_img = img.convert('RGB')
                rgb_img.save(top_image_dest, format='JPEG')
            except Exception:
                shutil.copy2(heading_img_path, top_image_dest)
        else:
            # Use default static top image
            top_image_src = os.path.join(settings.MEDIA_ROOT, 'websites', 'title-background.jpg')
            if os.path.exists(top_image_src):
                shutil.copy2(top_image_src, top_image_dest)
        # Copy favicon and logo if they exist
        favicon_path = ''
        logo_path = ''
        if website.favicon:
            favicon_dest = os.path.join(top_image_dest_dir, os.path.basename(str(website.favicon.name)))
            favicon_src = get_file_local_path_or_download(website.favicon, favicon_dest)
            if favicon_src and os.path.exists(favicon_dest):
                favicon_path = f"/media/websites/{os.path.basename(favicon_dest)}"
        if website.logo:
            logo_dest = os.path.join(top_image_dest_dir, os.path.basename(str(website.logo.name)))
            logo_src = get_file_local_path_or_download(website.logo, logo_dest)
            if logo_src and os.path.exists(logo_dest):
                logo_path = f"/media/websites/{os.path.basename(logo_dest)}"
        # Copy author logo if exists
        author_logo_path = ''
        if website.author and website.author.logo:
            author_logo_dest = os.path.join(top_image_dest_dir, os.path.basename(str(website.author.logo.name)))
            author_logo_src = get_file_local_path_or_download(website.author.logo, author_logo_dest)
            if author_logo_src and os.path.exists(author_logo_dest):
                author_logo_path = f"/media/websites/{os.path.basename(author_logo_dest)}"
        
        # Copy all CKEditor uploaded media files
        ckeditor_upload_source_path = os.path.join(settings.MEDIA_ROOT, settings.CKEDITOR_UPLOAD_PATH)
        ckeditor_upload_dest_path = os.path.join(media_dir, settings.CKEDITOR_UPLOAD_PATH)
        if os.path.exists(ckeditor_upload_source_path):
            shutil.copytree(ckeditor_upload_source_path, ckeditor_upload_dest_path, dirs_exist_ok=True)
        
        # Get homepage and pages
        homepage = website.pages.filter(is_homepage=True).first()
        if not homepage:
            homepage = website.pages.first()
        
        # Generate static site files with actual data
        static_settings = render_to_string('websites/static_settings.py', {
            'website': website,
        })
        
        static_urls = f'''from django.urls import path, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('home/', RedirectView.as_view(url='/')),
    path('sitemap.xml', views.sitemap, name='sitemap'),
    path('robots.txt', views.robots, name='robots'),
    path('disclaimer/', views.disclaimer, name='disclaimer'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('terms-of-service/', views.terms_of_service, name='terms_of_service'),
    path('contact/', views.contact, name='contact'),
'''

        # Add URLs for all pages
        for page in website.pages.all():
            if not page.is_homepage:
                static_urls += f'''    path('{page.slug}/', views.page, kwargs={{'slug': '{page.slug}'}}, name='{page.slug}'),
'''
        # Add catch-all redirect to home
        static_urls += ''']\n\nif settings.DEBUG:\n    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)\n'''
        
        # --- PATCH: Rewrite images in page content to local paths ---
        pages = website.pages.all()
        rewritten_pages_dict = {}
        for page in pages:
            new_content = download_and_rewrite_images(page.content, media_dir, website.id, page.id)
            rewritten_pages_dict[page.slug] = {
                'title': page.title,
                'content': new_content,
                'is_homepage': page.is_homepage,
                'date_published': page.date_published.isoformat() if page.date_published else '',
                'date_modified': page.date_modified.isoformat() if page.date_modified else '',
                'breadcrumb': page.breadcrumb,
                'paragraphs': [p.strip() for p in re.split(r'<br ?/?>|\n', new_content) if p.strip() and p.strip() != '&nbsp;'],
            }
        # --- END PATCH ---

        # --- PATCH: Ensure default form options for export ---
        export_form_options1 = website.form_options1
        if not export_form_options1 or (isinstance(export_form_options1, str) and export_form_options1.strip() == ''):
            export_form_options1 = [p.title for p in website.pages.all() if not p.is_homepage]
        else:
            export_form_options1 = [opt.strip() for opt in export_form_options1.split('\n') if opt.strip()]
        export_form_options2 = website.form_options2
        if not export_form_options2 or (isinstance(export_form_options2, str) and export_form_options2.strip() == ''):
            export_form_options2 = ['Less than 300', 'Between 300-500', 'More than 500']
        else:
            export_form_options2 = [opt.strip() for opt in export_form_options2.split('\n') if opt.strip()]
        # --- END PATCH ---

        # Parse social links for export
        import re
        def parse_social_links(markdown_text):
            pattern = r'\[([^\]]+)\]\(([^)]+)\)'
            return [{'title': m[0], 'url': m[1]} for m in re.findall(pattern, markdown_text or "")]
        export_social_links = parse_social_links(website.social_media_box)

        static_data_dict = {
            'name': website.name,
            'domain': website.domain,
            'phone_number_display': website.phone_number_display,
            'phone_number_link': website.phone_number_link,
            'robots_txt': website.robots_txt,
            'github_repo': website.github_repo,
            'is_public_repo': website.is_public_repo,
            'form_cta1': website.form_cta1,
            'form_cta2': website.form_cta2,
            'form_question1': website.form_question1,
            'form_question2': website.form_question2,
            'form_options1': export_form_options1,
            'form_options2': export_form_options2,
            'form_quote_button': website.form_quote_button,
            'form_name_label': website.form_name_label,
            'form_phone_label': website.form_phone_label,
            'form_email_label': website.form_email_label,
            'footer_phone_cta': website.footer_phone_cta,
            'footer_legal_disclaimer': website.footer_legal_disclaimer,
            'google_search_console_tag': website.google_search_console_tag,
            'google_tag': website.google_tag,
            'meta_facebook_pixel': website.meta_facebook_pixel,
            'google_analytics': website.google_analytics,
            'social_links': export_social_links,
            'favicon': favicon_path,
            'logo': logo_path,
            'author': {
                'name': website.author.name if website.author else '',
                'logo': author_logo_path,
                'description': website.author.description if website.author else '',
                'image': website.author.image if website.author else '',
                'url': website.author.url if website.author else '',
            },
            'global_seo_schema': website.global_seo_schema,
            'WEB3_FORM_API_KEY': os.getenv('WEB3_FORM_API_KEY', ''),
            'NOFOLLOW_URLS': [f'/{p.slug}' for p in website.pages.filter(nofollow_document=True)],
            'header_box_color': website.header_box_color or "#14808a55",
            'phone_banner_bg_color': website.phone_banner_bg_color or '#14808a',
            'contact_box_color': website.contact_box_color or "#104ef930",
        }
        static_data_content = (
            "# Website data\n"
            f"WEBSITE = {repr(static_data_dict)}\n"
            f"PAGES = {repr(rewritten_pages_dict)}\n"
            f"HOMEPAGE_SLUG = {repr(homepage.slug if homepage else '')}\n"
            f"HEADER_MENU = {repr(header_menu_parsed)}\n"
            f"FOOTER_MENU = {repr(footer_menu_parsed)}\n"
        )
                    
        static_views = '''from django.shortcuts import render
from django.http import HttpResponse
from .static_data import WEBSITE, PAGES, HOMEPAGE_SLUG, HEADER_MENU, FOOTER_MENU
import json
from bs4 import BeautifulSoup
import os
import re


def filename_to_alt(filename):
    base = os.path.basename(filename)
    name, _ = os.path.splitext(base)

    # Try to find content in first set of parentheses
    match = re.search(r'\(([^)]+)\)', name)
    if match:
        text = match.group(1)
    else:
        text = name

    # Replace underscores with spaces and capitalize each word
    return " ".join(word.capitalize() for word in text.replace("_", " ").split())
    
def set_img_alt_tags(html):
    soup = BeautifulSoup(html, "html.parser")
    for img in soup.find_all("img"):
        if not img.has_attr("alt") or not img["alt"]:
            src = img.get("src", "")
            img["alt"] = filename_to_alt(src)
            img["loading"] = "lazy"
    return str(soup)
def add_nofollow(html, nofollow_urls):
    """
    Adds rel="nofollow" to <a> tags whose href matches any in nofollow_urls.
    Usage: {{ html|add_nofollow:nofollow_urls }}
    """
    if not html or not nofollow_urls:
        return html
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        if a['href'] in nofollow_urls:
            rel = a.get('rel', [])
            if "nofollow" not in rel:
                rel.append("nofollow")
            a['rel'] = " ".join(rel)
    return str(soup) 
def home(request):
    page_data = PAGES[HOMEPAGE_SLUG]
    if "content" in page_data:
        page_data["content"] = set_img_alt_tags(page_data["content"])
    global_schema = WEBSITE.get('global_seo_schema', '')
    per_page_schema = json.dumps({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": page_data.get('title', ''),
        "description": page_data.get('content', '')[:150] if 'content' in page_data else '',
        "datePublished": page_data.get('date_published', ''),
        "dateModified": page_data.get('date_modified', ''),
        "author": {
            "@type": "Organization",
            "name": WEBSITE.get('name', '')
        },
        "publisher": {
            "@type": "Organization",
            "name": WEBSITE.get('name', ''),
            "logo": {
                "@type": "ImageObject",
                "url": WEBSITE.get('logo', '')
            }
        },
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": WEBSITE.get('domain', '') + '/' + page_data.get('slug', '')
        }
    }, ensure_ascii=False, indent=2)
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    is_search_bot = 'googlebot' in user_agent or 'bingbot' in user_agent
    return render(request, 'static_page.html', {
        'website': WEBSITE,
        'page': page_data,
        'header_menu': HEADER_MENU,
        'footer': FOOTER_MENU,
        'all_pages': list(PAGES.values()),
        'global_schema': global_schema,
        'per_page_schema': per_page_schema,
        'is_search_bot': is_search_bot
    })

def page(request, slug):
    page_data = PAGES[slug]
    if "content" in page_data:
        page_data["content"] = set_img_alt_tags(page_data["content"])
    global_schema = WEBSITE.get('global_seo_schema', '')
    per_page_schema = json.dumps({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": page_data.get('title', ''),
        "description": page_data.get('content', '')[:150] if 'content' in page_data else '',
        "datePublished": page_data.get('date_published', ''),
        "dateModified": page_data.get('date_modified', ''),
        "author": {
            "@type": "Organization",
            "name": WEBSITE.get('name', '')
        },
        "publisher": {
            "@type": "Organization",
            "name": WEBSITE.get('name', ''),
            "logo": {
                "@type": "ImageObject",
                "url": WEBSITE.get('logo', '')
            }
        },
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": WEBSITE.get('domain', '') + '/' + slug
        }
    }, ensure_ascii=False, indent=2)
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    is_search_bot = 'googlebot' in user_agent or 'bingbot' in user_agent
    return render(request, 'static_page.html', {
        'website': WEBSITE,
        'page': page_data,
        'header_menu': HEADER_MENU,
        'footer': FOOTER_MENU,
        'all_pages': list(PAGES.values()),
        'global_schema': global_schema,
        'per_page_schema': per_page_schema,
        'is_search_bot': is_search_bot
    })

def sitemap(request):
    return render(request, 'sitemap.xml', {{
        'website': WEBSITE,
        'pages': PAGES
    }}, content_type='application/xml')

def robots(request):
    content = 'User-agent: *\\nAllow: /\\nSitemap: https://' + WEBSITE["domain"] + '/sitemap.xml'
    return HttpResponse(content, content_type='text/plain')

def disclaimer(request):
    return render(request, 'static_page.html', {{
        'website': WEBSITE,
        'page': {{'title': 'Disclaimer', 'content': 'This is the disclaimer page.'}},
        'header_menu': HEADER_MENU,
        'footer': FOOTER_MENU,
        'all_pages': list(PAGES.values())
    }})

def privacy_policy(request):
    return render(request, 'static_page.html', {{
        'website': WEBSITE,
        'page': {{'title': 'Privacy Policy', 'content': 'This is the privacy policy page.'}},
        'header_menu': HEADER_MENU,
        'footer': FOOTER_MENU,
        'all_pages': list(PAGES.values())
    }})

def terms_of_service(request):
    return render(request, 'static_page.html', {{
        'website': WEBSITE,
        'page': {{'title': 'Terms of Service', 'content': 'This is the terms of service page.'}},
        'header_menu': HEADER_MENU,
        'footer': FOOTER_MENU,
        'all_pages': list(PAGES.values())
    }})

def contact(request):
    content_string = 'Contact us at ' + WEBSITE["phone_number_display"]
    return render(request, 'static_page.html', {{
        'website': WEBSITE,
        'page': {{'title': 'Contact', 'content': content_string}},
        'header_menu': HEADER_MENU,
        'footer': FOOTER_MENU,
        'all_pages': list(PAGES.values())
    }})
'''
        
        # After constructing static_views, fix robots.txt and curly braces for valid Python
        static_views = static_views.replace("content = 'User-agent: *\nAllow: /\nSitemap: https://' + WEBSITE[\"domain\"] + '/sitemap.xml'", "content = 'User-agent: *\\nAllow: /\\nSitemap: https://' + WEBSITE[\"domain\"] + '/sitemap.xml'")
        static_views = static_views.replace('{{', '{').replace('}}', '}')
        
        # Generate robots.txt content
        robots_txt_content = f'User-agent: *\\nAllow: /\\nSitemap: https://{website.domain}/sitemap.xml'

        # Create manage.py
        manage_py_content = '''#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "static_site.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed?"
        ) from exc
    execute_from_command_line(sys.argv)
'''
        
        # Create wsgi.py
        wsgi_content = '''import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'static_site.settings')
application = get_wsgi_application()
'''
        
        # Create asgi.py
        asgi_content = '''import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'static_site.settings')
application = get_asgi_application()
'''
        
        # Create requirements.txt
        requirements_content = 'Django==5.0.2\nPillow==10.2.0\ngunicorn\ndjango-redis\nbs4'
        
        # Write files
        with open(os.path.join(static_site_dir, 'settings.py'), 'w') as f:
            f.write(static_settings)
        
        with open(os.path.join(static_site_dir, 'urls.py'), 'w') as f:
            f.write(static_urls)
            
        with open(os.path.join(static_site_dir, 'views.py'), 'w') as f:
            f.write(static_views)
            
        with open(os.path.join(static_site_dir, 'static_data.py'), 'w') as f:
            f.write(static_data_content)
            
        with open(os.path.join(temp_dir, 'robots.txt'), 'w') as f:
            f.write(robots_txt_content)

        with open(os.path.join(static_site_dir, 'wsgi.py'), 'w') as f:
            f.write(wsgi_content)
            
        with open(os.path.join(static_site_dir, 'asgi.py'), 'w') as f:
            f.write(asgi_content)
            
        with open(os.path.join(temp_dir, 'manage.py'), 'w') as f:
            f.write(manage_py_content)
            
        with open(os.path.join(temp_dir, 'requirements.txt'), 'w') as f:
            f.write(requirements_content)
        
        # Create __init__.py in static_site directory
        with open(os.path.join(static_site_dir, '__init__.py'), 'w') as f:
            f.write('')
        
        # Create zip file
        zip_path = os.path.join(temp_dir, f'{website.domain}.zip')
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file.endswith('.zip'):
                        continue
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zipf.write(file_path, arcname)
        
        # Return the zip file
        with open(zip_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="{website.domain}.zip"'
            return response

@login_required
def github_integration(request, website_id):
    website = get_object_or_404(Website, id=website_id, owner=request.user)
    
    # Fetch existing repositories for the dropdown
    existing_repos = []
    try:
        g = Github(settings.GITHUB_TOKEN)
        user = g.get_user()
        repos = user.get_repos()
        existing_repos = [repo.name for repo in repos]
    except Exception as e:
        print(f"Error fetching GitHub repos: {e}")
    
    if request.method == 'POST':
        form = GitHubRepoForm(request.POST, repos=existing_repos, connected_repo=website.github_repo)
        if form.is_valid():
            try:
                g = Github(settings.GITHUB_TOKEN)
                print("github token:", settings.GITHUB_TOKEN)
                user = g.get_user()
                repo_name = form.cleaned_data.get('repo_name')
                existing_repo_selected = form.cleaned_data.get('existing_repo')
                repo = None
                # If no repo_name and a connected repo exists, push to the connected repo
                if not repo_name and website.github_repo:
                    # Extract owner and repo name from the connected repo URL
                    # Example: https://github.com/owner/repo.git
                    import re
                    m = re.match(r'https://github.com/([^/]+)/([^/.]+)', website.github_repo)
                    if m:
                        owner, repo_name_from_url = m.group(1), m.group(2)
                        repo = g.get_repo(f"{owner}/{repo_name_from_url}")
                        print(f"Pushing to already connected repo: {repo.full_name}")
                    else:
                        raise Exception("Could not parse connected repo URL.")
                elif existing_repo_selected:
                    repo = user.get_repo(repo_name)
                    print(f"Using existing repo: {repo.name}")
                else:
                    # Create new repository (default to private)
                    try:
                        repo = user.get_repo(repo_name)
                        print(f"Repository {repo_name} already exists, using it")
                    except Exception:
                        repo = user.create_repo(repo_name, private=True)  # Default to private
                        print(f"Created new repo: {repo.name}, is_public: {not repo.private}")

                with tempfile.TemporaryDirectory() as temp_dir:
                    write_static_site_files(temp_dir, website)  # Write ALL files first
                    time.sleep(1)  # Ensure files are flushed to disk

                    # --- Git Operations ---
                    git_repo = git.Repo.init(temp_dir)
                    git_repo.config_writer().set_value("user", "name", user.login).release()
                    git_repo.config_writer().set_value("user", "email", user.email or f"{user.login}@users.noreply.github.com").release()

                    remote_url = f"https://{settings.GITHUB_TOKEN}@github.com/{repo.owner.login}/{repo.name}.git"
                    if "origin" not in git_repo.remotes:
                        git_repo.create_remote("origin", remote_url)
                    else:
                        git_repo.remotes.origin.set_url(remote_url)

                    git_repo.git.add(A=True)  # Add ALL files from temp_dir
                    if git_repo.is_dirty(untracked_files=True):
                        git_repo.index.commit(f"Update site: {website.name}")
                        git_repo.remotes.origin.push(refspec='HEAD:main', force=True)
                    git_repo.close()

                website.github_repo = repo.clone_url
                website.is_public_repo = not repo.private  # Use the actual repository privacy setting
                website.save()
                messages.success(request, f'Website successfully pushed to {repo.full_name}!')
                return redirect('dashboard')

            except Exception as e:
                messages.error(request, f'Error during GitHub integration: {str(e)}')
    else:
        # Don't pre-fill the repo name field to avoid confusion
        # Let user either enter a new name or select from existing
        form = GitHubRepoForm(repos=existing_repos)

    return render(request, 'websites/github_integration.html', {'form': form, 'website': website})

@login_required
def delete_website(request, website_id):
    website = get_object_or_404(Website, id=website_id, owner=request.user)
    website.delete()
    messages.success(request, 'Website deleted successfully!')
    return redirect('dashboard')

@login_required
def delete_page(request, website_id, page_id):
    website = get_object_or_404(Website, id=website_id, owner=request.user)
    page = get_object_or_404(Page, id=page_id, website=website)
    page.delete()
    messages.success(request, 'Page deleted successfully!')
    return redirect('manage_pages', website_id=website.id)

@login_required
def edit_menus(request, website_id):
    website = get_object_or_404(Website, id=website_id, owner=request.user)
    header_menu, _ = website.menus.get_or_create(type='header', defaults={'content': ''})
    footer_menu, _ = website.menus.get_or_create(type='footer', defaults={'content': ''})

    if request.method == 'POST':
        header_form = MenuForm(request.POST, prefix='header', instance=header_menu, website=website)
        footer_form = MenuForm(request.POST, prefix='footer', instance=footer_menu, website=website)
        if header_form.is_valid() and footer_form.is_valid():
            header_form.save()
            footer_form.save()
            messages.success(request, 'Menus updated successfully!')
            return redirect('edit_menus', website_id=website.id)
    else:
        header_form = MenuForm(prefix='header', instance=header_menu, website=website)
        footer_form = MenuForm(prefix='footer', instance=footer_menu, website=website)
    nofollow_urls = [f'/{p.slug}' for p in website.pages.filter(nofollow_document=True)]
    return render(request, 'websites/edit_menus.html', {
        'website': website,
        'header_form': header_form,
        'footer_form': footer_form,
        'nofollow_urls': nofollow_urls,
    })

@login_required
def edit_site_settings(request, website_id):
    website = get_object_or_404(Website, id=website_id, owner=request.user)
    if request.method == 'POST':
        form = WebsiteSettingsForm(request.POST, request.FILES, instance=website)
        if form.is_valid():
            form.save()
            messages.success(request, 'Site settings updated successfully!')
            return redirect('manage_pages', website_id=website.id)
    else:
        form = WebsiteSettingsForm(instance=website)
    return render(request, 'websites/edit_site_settings.html', {'form': form, 'website': website})

@login_required
def tracking_settings(request, website_id):
    website = get_object_or_404(Website, id=website_id, owner=request.user)
    if request.method == 'POST':
        form = TrackingSettingsForm(request.POST, instance=website)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tracking settings updated successfully!')
            return redirect('manage_pages', website_id=website.id)
    else:
        form = TrackingSettingsForm(instance=website)
    return render(request, 'websites/edit_tracking_settings.html', {'form': form, 'website': website})

@login_required
def form_settings(request, website_id):
    website = get_object_or_404(Website, id=website_id, owner=request.user)
    if request.method == 'POST':
        form = FormSettingsForm(request.POST, instance=website)
        if form.is_valid():
            form.save()
            messages.success(request, 'Form settings updated successfully!')
            return redirect('manage_pages', website_id=website.id)
    else:
        form = FormSettingsForm(instance=website)
    return render(request, 'websites/edit_form_settings.html', {'form': form, 'website': website})

@login_required
def edit_author(request, website_id):
    website = get_object_or_404(Website, id=website_id, owner=request.user)
    author = website.author or Author.objects.create()
    if request.method == 'POST':
        form = AuthorForm(request.POST, request.FILES, instance=author)
        if form.is_valid():
            author = form.save()
            website.author = author
            website.save()
            messages.success(request, 'Author updated successfully!')
            return redirect('manage_pages', website_id=website.id)
    else:
        form = AuthorForm(instance=author)
    return render(request, 'websites/edit_author.html', {'form': form, 'website': website, 'author': author})

# Place the helper at module level (not inside another function)
def write_static_site_files(temp_dir, website):
    import re
    from django.template.loader import render_to_string
    import os, shutil
    from PIL import Image
    static_site_dir = os.path.join(temp_dir, 'static_site')
    static_dir = os.path.join(temp_dir, 'static')
    media_dir = os.path.join(temp_dir, 'media')
    templates_dir = os.path.join(temp_dir, 'templates')
    os.makedirs(static_site_dir, exist_ok=True)
    os.makedirs(static_dir, exist_ok=True)
    os.makedirs(media_dir, exist_ok=True)
    os.makedirs(templates_dir, exist_ok=True)
    # Copy static files
    static_files = ['css/bootstrap.min.css', 'js/bootstrap.bundle.min.js']
    for static_file in static_files:
        src_path = os.path.join(settings.STATIC_ROOT, static_file)
        if os.path.exists(src_path):
            dest_path = os.path.join(static_dir, static_file)
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copy2(src_path, dest_path)
    # Copy templates
    template_files = ['static_base.html', 'static_page.html', '404.html', 'sitemap.xml']
    for template_file in template_files:
        src_path = os.path.join(settings.BASE_DIR, 'templates', 'websites', template_file)
        if os.path.exists(src_path):
            dest_path = os.path.join(templates_dir, template_file)
            shutil.copy2(src_path, dest_path)
    # Copy the static top image for all websites
    top_image_dest_dir = os.path.join(media_dir, 'websites')
    os.makedirs(top_image_dest_dir, exist_ok=True)
    def get_file_local_path_or_download(field, dest_path):
        if field:
            try:
                file_path = field.path
                if os.path.exists(file_path):
                    return file_path
            except Exception:
                try:
                    url = field.url
                    r = requests.get(url, stream=True, timeout=5)
                    if r.status_code == 200:
                        with open(dest_path, 'wb') as f:
                            for chunk in r.iter_content(1024):
                                f.write(chunk)
                        return dest_path
                except Exception:
                    pass
        return None
    top_image_dest = os.path.join(top_image_dest_dir, 'title-background.jpg')
    heading_img_field = website.heading_background_image
    heading_img_path = get_file_local_path_or_download(heading_img_field, top_image_dest)
    if heading_img_path and os.path.exists(heading_img_path):
        try:
            img = Image.open(heading_img_path)
            rgb_img = img.convert('RGB')
            rgb_img.save(top_image_dest, format='JPEG')
        except Exception:
            shutil.copy2(heading_img_path, top_image_dest)
    else:
        top_image_src = os.path.join(settings.MEDIA_ROOT, 'websites', 'title-background.jpg')
        if os.path.exists(top_image_src):
            shutil.copy2(top_image_src, top_image_dest)
    favicon_path = ''
    logo_path = ''
    if website.favicon:
        favicon_dest = os.path.join(top_image_dest_dir, os.path.basename(str(website.favicon.name)))
        favicon_src = get_file_local_path_or_download(website.favicon, favicon_dest)
        if favicon_src and os.path.exists(favicon_dest):
            favicon_path = f"/media/websites/{os.path.basename(favicon_dest)}"
    if website.logo:
        logo_dest = os.path.join(top_image_dest_dir, os.path.basename(str(website.logo.name)))
        logo_src = get_file_local_path_or_download(website.logo, logo_dest)
        if logo_src and os.path.exists(logo_dest):
            logo_path = f"/media/websites/{os.path.basename(logo_dest)}"
    # Copy author logo if exists
    author_logo_path = ''
    if website.author and website.author.logo:
        author_logo_dest = os.path.join(top_image_dest_dir, os.path.basename(str(website.author.logo.name)))
        author_logo_src = get_file_local_path_or_download(website.author.logo, author_logo_dest)
        if author_logo_src and os.path.exists(author_logo_dest):
            author_logo_path = f"/media/websites/{os.path.basename(author_logo_dest)}"
    ckeditor_upload_source_path = os.path.join(settings.MEDIA_ROOT, settings.CKEDITOR_UPLOAD_PATH)
    ckeditor_upload_dest_path = os.path.join(media_dir, settings.CKEDITOR_UPLOAD_PATH)
    if os.path.exists(ckeditor_upload_source_path):
        shutil.copytree(ckeditor_upload_source_path, ckeditor_upload_dest_path, dirs_exist_ok=True)
    homepage = website.pages.filter(is_homepage=True).first() or website.pages.first()
    # --- Compose all content as in export_website ---
    static_settings = render_to_string('websites/static_settings.py', {'website': website})
    # static_urls
    static_urls = (
        'from django.urls import path\n'
        'from django.conf import settings\n'
        'from django.conf.urls.static import static\n'
        'from django.views.generic import RedirectView\n'
        'from . import views\n\n'
        'urlpatterns = [\n'
        '    path(\'\', views.home, name=\'home\'),\n'
        '    path(\'home/\', RedirectView.as_view(url=\'/\')),\n'
        '    path(\'sitemap.xml\', views.sitemap, name=\'sitemap\'),\n'
        '    path(\'robots.txt\', views.robots, name=\'robots\'),\n'
        '    path(\'disclaimer/\', views.disclaimer, name=\'disclaimer\'),\n'
        '    path(\'privacy-policy/\', views.privacy_policy, name=\'privacy_policy\'),\n'
        '    path(\'terms-of-service/\', views.terms_of_service, name=\'terms_of_service\'),\n'
        '    path(\'contact/\', views.contact, name=\'contact\'),\n'
    )
    for page in website.pages.all():
        if not page.is_homepage:
            static_urls += f"    path('{page.slug}/', views.page, kwargs={{'slug': '{page.slug}'}}, name='{page.slug}'),\n"
    static_urls += ''']\n\nif settings.DEBUG:\n    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)\n'''
        
    # static_data_content
    pages_dict = {}
    for p in website.pages.all():
        new_content = download_and_rewrite_images(p.content, media_dir, website.id, p.id)
        pages_dict[p.slug] = {
            'title': p.title,
            'content': new_content,
            'is_homepage': p.is_homepage,
            'date_published': p.date_published.isoformat() if p.date_published else '',
            'date_modified': p.date_modified.isoformat() if p.date_modified else '',
            'breadcrumb': p.breadcrumb,
            'paragraphs': [para.strip() for para in re.split(r'<br ?/?>|\n', new_content) if para.strip() and para.strip() != '&nbsp;'],
        }
    export_form_options1 = website.form_options1
    if not export_form_options1 or (isinstance(export_form_options1, str) and export_form_options1.strip() == ''):
        export_form_options1 = [p.title for p in website.pages.all() if not p.is_homepage]
    else:
        export_form_options1 = [opt.strip() for opt in export_form_options1.split('\n') if opt.strip()]
    export_form_options2 = website.form_options2
    if not export_form_options2 or (isinstance(export_form_options2, str) and export_form_options2.strip() == ''):
        export_form_options2 = ['Less than 300', 'Between 300-500', 'More than 500']
    else:
        export_form_options2 = [opt.strip() for opt in export_form_options2.split('\n') if opt.strip()]
    def parse_social_links(markdown_text):
        pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        return [{'title': m[0], 'url': m[1]} for m in re.findall(pattern, markdown_text or "")]
    export_social_links = parse_social_links(website.social_media_box)
    header_menu = website.menus.filter(type='header').first()
    footer_menu = website.menus.filter(type='footer').first()
    header_menu_content = header_menu.content if header_menu else ''
    footer_menu_content = footer_menu.content if footer_menu else ''
    def parse_menu_markdown(md):
        lines = md.splitlines()
        stack = []
        root = []
        paragraphs = []
        for line in lines:
            if not line.strip():
                continue
            depth = 0
            orig_line = line
            while line.startswith('\t'):
                depth += 1
                line = line[1:]
            m = re.match(r'\[(.*?)\]\((.*?)\)', line.strip())
            if m:
                title, url = m.groups()
                if url and not url.startswith(('http://', 'https://', '/')):
                    url = '/' + url.lstrip('/')
                node = {'title': title, 'url': url, 'children': []}
                if depth == 0:
                    root.append(node)
                    stack = [node]
                else:
                    if len(stack) >= depth:
                        stack = stack[:depth]
                    if stack:
                        stack[-1]['children'].append(node)
                    stack.append(node)
            else:
                if depth == 0:
                    paragraphs.append(orig_line.strip())
        return {'paragraphs': paragraphs, 'links': root}
    header_menu_parsed = parse_menu_markdown(header_menu_content)
    footer_menu_parsed = parse_menu_markdown(footer_menu_content)
    static_data_dict = {
        'name': website.name,
        'domain': website.domain,
        'phone_number_display': website.phone_number_display,
        'phone_number_link': website.phone_number_link,
        'robots_txt': website.robots_txt,
        'github_repo': website.github_repo,
        'is_public_repo': website.is_public_repo,
        'form_cta1': website.form_cta1,
        'form_cta2': website.form_cta2,
        'form_question1': website.form_question1,
        'form_question2': website.form_question2,
        'form_options1': export_form_options1,
        'form_options2': export_form_options2,
        'form_quote_button': website.form_quote_button,
        'form_name_label': website.form_name_label,
        'form_phone_label': website.form_phone_label,
        'form_email_label': website.form_email_label,
        'footer_phone_cta': website.footer_phone_cta,
        'footer_legal_disclaimer': website.footer_legal_disclaimer,
        'google_search_console_tag': website.google_search_console_tag,
        'google_tag': website.google_tag,
        'meta_facebook_pixel': website.meta_facebook_pixel,
        'google_analytics': website.google_analytics,
        'social_links': export_social_links,
        'favicon': favicon_path,
        'logo': logo_path,
        'author': {
            'name': website.author.name if website.author else '',
            'logo': author_logo_path,
            'description': website.author.description if website.author else '',
            'image': website.author.image if website.author else '',
            'url': website.author.url if website.author else '',
        },
        'global_seo_schema': website.global_seo_schema,
        'WEB3_FORM_API_KEY': os.getenv('WEB3_FORM_API_KEY', ''),
        'NOFOLLOW_URLS': [f'/{p.slug}' for p in website.pages.filter(nofollow_document=True)],
        'header_box_color': website.header_box_color or "#14808a55",
        'phone_banner_bg_color': website.phone_banner_bg_color or '#14808a',
        'contact_box_color': website.contact_box_color or "#24d16cff",
        'header_box_rgba': hex_to_rgba(website.header_box_color or '#14808a', 0.5),
    }
    static_data_content = (
        "# Website data\n"
        f"WEBSITE = {repr(static_data_dict)}\n"
        f"PAGES = {repr(pages_dict)}\n"
        f"HOMEPAGE_SLUG = {repr(homepage.slug if homepage else '')}\n"
        f"HEADER_MENU = {repr(header_menu_parsed)}\n"
        f"FOOTER_MENU = {repr(footer_menu_parsed)}\n"
    )
    # static_views
    static_views = '''from django.shortcuts import render
from django.http import HttpResponse
from .static_data import WEBSITE, PAGES, HOMEPAGE_SLUG, HEADER_MENU, FOOTER_MENU
import json
from bs4 import BeautifulSoup
import os
import re


def filename_to_alt(filename):
    base = os.path.basename(filename)
    name, _ = os.path.splitext(base)

    # Try to find content in first set of parentheses
    match = re.search(r'\(([^)]+)\)', name)
    if match:
        text = match.group(1)
    else:
        text = name

    # Replace underscores with spaces and capitalize each word
    return " ".join(word.capitalize() for word in text.replace("_", " ").split())
    
def set_img_alt_tags(html):
    soup = BeautifulSoup(html, "html.parser")
    for img in soup.find_all("img"):
        if not img.has_attr("alt") or not img["alt"]:
            src = img.get("src", "")
            img["alt"] = filename_to_alt(src)
            img["loading"] = "lazy"
    return str(soup)
def add_nofollow(html, nofollow_urls):
    """
    Adds rel="nofollow" to <a> tags whose href matches any in nofollow_urls.
    Usage: {{ html|add_nofollow:nofollow_urls }}
    """
    if not html or not nofollow_urls:
        return html
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        if a['href'] in nofollow_urls:
            rel = a.get('rel', [])
            if "nofollow" not in rel:
                rel.append("nofollow")
            a['rel'] = " ".join(rel)
    return str(soup) 
def home(request):
    page_data = PAGES[HOMEPAGE_SLUG]
    if "content" in page_data:
        page_data["content"] = set_img_alt_tags(page_data["content"])
    global_schema = WEBSITE.get('global_seo_schema', '')
    per_page_schema = json.dumps({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": page_data.get('title', ''),
        "description": page_data.get('content', '')[:150] if 'content' in page_data else '',
        "datePublished": page_data.get('date_published', ''),
        "dateModified": page_data.get('date_modified', ''),
        "author": {
            "@type": "Organization",
            "name": WEBSITE.get('name', '')
        },
        "publisher": {
            "@type": "Organization",
            "name": WEBSITE.get('name', ''),
            "logo": {
                "@type": "ImageObject",
                "url": WEBSITE.get('logo', '')
            }
        },
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": WEBSITE.get('domain', '') + '/' + page_data.get('slug', '')
        }
    }, ensure_ascii=False, indent=2)
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    is_search_bot = 'googlebot' in user_agent or 'bingbot' in user_agent
    return render(request, 'static_page.html', {
        'website': WEBSITE,
        'page': page_data,
        'header_menu': HEADER_MENU,
        'footer': FOOTER_MENU,
        'all_pages': list(PAGES.values()),
        'global_schema': global_schema,
        'per_page_schema': per_page_schema,
        'is_search_bot': is_search_bot
    })

def page(request, slug):
    page_data = PAGES[slug]
    if "content" in page_data:
        page_data["content"] = set_img_alt_tags(page_data["content"])
    global_schema = WEBSITE.get('global_seo_schema', '')
    per_page_schema = json.dumps({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": page_data.get('title', ''),
        "description": page_data.get('content', '')[:150] if 'content' in page_data else '',
        "datePublished": page_data.get('date_published', ''),
        "dateModified": page_data.get('date_modified', ''),
        "author": {
            "@type": "Organization",
            "name": WEBSITE.get('name', '')
        },
        "publisher": {
            "@type": "Organization",
            "name": WEBSITE.get('name', ''),
            "logo": {
                "@type": "ImageObject",
                "url": WEBSITE.get('logo', '')
            }
        },
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": WEBSITE.get('domain', '') + '/' + slug
        }
    }, ensure_ascii=False, indent=2)
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    is_search_bot = 'googlebot' in user_agent or 'bingbot' in user_agent
    return render(request, 'static_page.html', {
        'website': WEBSITE,
        'page': page_data,
        'header_menu': HEADER_MENU,
        'footer': FOOTER_MENU,
        'all_pages': list(PAGES.values()),
        'global_schema': global_schema,
        'per_page_schema': per_page_schema,
        'is_search_bot': is_search_bot
    })

def sitemap(request):
    return render(request, 'sitemap.xml', {
        'website': WEBSITE,
        'pages': PAGES
    }, content_type='application/xml')

def robots(request):
    content = 'User-agent: *\nAllow: /\nSitemap: https://' + WEBSITE["domain"] + '/sitemap.xml'
    return HttpResponse(content, content_type='text/plain')

def disclaimer(request):
    return render(request, 'static_page.html', {
        'website': WEBSITE,
        'page': {'title': 'Disclaimer', 'content': 'This is the disclaimer page.'},
        'header_menu': HEADER_MENU,
        'footer': FOOTER_MENU,
        'all_pages': list(PAGES.values())
    })

def privacy_policy(request):
    return render(request, 'static_page.html', {
        'website': WEBSITE,
        'page': {'title': 'Privacy Policy', 'content': 'This is the privacy policy page.'},
        'header_menu': HEADER_MENU,
        'footer': FOOTER_MENU,
        'all_pages': list(PAGES.values())
    })

def terms_of_service(request):
    return render(request, 'static_page.html', {
        'website': WEBSITE,
        'page': {'title': 'Terms of Service', 'content': 'This is the terms of service page.'},
        'header_menu': HEADER_MENU,
        'footer': FOOTER_MENU,
        'all_pages': list(PAGES.values())
    })

def contact(request):
    content_string = 'Contact us at ' + WEBSITE["phone_number_display"]
    return render(request, 'static_page.html', {
        'website': WEBSITE,
        'page': {'title': 'Contact', 'content': content_string},
        'header_menu': HEADER_MENU,
        'footer': FOOTER_MENU,
        'all_pages': list(PAGES.values())
    })
'''
          
    static_views = static_views.replace("content = 'User-agent: *\nAllow: /\nSitemap: https://' + WEBSITE[\"domain\"] + '/sitemap.xml'", "content = 'User-agent: *\\nAllow: /\\nSitemap: https://' + WEBSITE[\"domain\"] + '/sitemap.xml'")
    static_views = static_views.replace('{{', '{').replace('}}', '}')
    robots_txt_content = f'User-agent: *\\nAllow: /\\nSitemap: https://{website.domain}/sitemap.xml'
    manage_py_content = '''#!/usr/bin/env python\nimport os\nimport sys\n\nif __name__ == "__main__":\n    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "static_site.settings")\n    try:\n        from django.core.management import execute_from_command_line\n    except ImportError as exc:\n        raise ImportError(\n            "Couldn't import Django. Are you sure it's installed?"\n        ) from exc\n    execute_from_command_line(sys.argv)\n'''
    wsgi_content = 'import os\nfrom django.core.wsgi import get_wsgi_application\n\nos.environ.setdefault(\'DJANGO_SETTINGS_MODULE\', \'static_site.settings\')\napplication = get_wsgi_application()\n'
    asgi_content = 'import os\nfrom django.core.asgi import get_asgi_application\n\nos.environ.setdefault(\'DJANGO_SETTINGS_MODULE\', \'static_site.settings\')\napplication = get_asgi_application()\n'
    requirements_content = 'Django==5.0.2\nPillow==10.2.0\ngunicorn\ndjango-redis\nbs4\n'
    _headers_content = '/media/*\nCache-Control: public, max-age=31536000'
    ngnix_conf_content = 'location /media/ {\nexpires 1y;\nadd_header Cache-Control "public";\n} '
    # --- Write all static_site and root-level files as in zip export ---
    with open(os.path.join(static_site_dir, 'settings.py'), 'w') as f:
        f.write(static_settings)
    with open(os.path.join(static_site_dir, 'urls.py'), 'w') as f:
        f.write(static_urls)
    with open(os.path.join(static_site_dir, 'views.py'), 'w') as f:
        f.write(static_views)
    with open(os.path.join(static_site_dir, 'static_data.py'), 'w') as f:
        f.write(static_data_content)
    with open(os.path.join(static_site_dir, '__init__.py'), 'w') as f:
        f.write('')
    with open(os.path.join(static_site_dir, 'wsgi.py'), 'w') as f:
        f.write(wsgi_content)
    with open(os.path.join(static_site_dir, 'asgi.py'), 'w') as f:
        f.write(asgi_content)
    with open(os.path.join(temp_dir, 'robots.txt'), 'w') as f:
        f.write(robots_txt_content)
    with open(os.path.join(temp_dir, 'manage.py'), 'w') as f:
        f.write(manage_py_content)
    with open(os.path.join(temp_dir, 'requirements.txt'), 'w') as f:
        f.write(requirements_content)
    with open(os.path.join(temp_dir, '_headers'), 'w') as f:
        f.write(_headers_content)
    with open(os.path.join(temp_dir, 'nginx.conf'), 'w') as f:
        f.write(ngnix_conf_content)

def download_and_rewrite_images(html_content, media_dir, website_id, page_id):
    soup = BeautifulSoup(html_content, 'html.parser')

    for tag in soup.find_all(src=True):
        src = tag.get('src')

        is_image_tag = tag.name == 'img' or (tag.name == 'input' and tag.get('type') == 'image')

        if src and src.startswith('http') and is_image_tag:
            try:
                response = requests.get(src, stream=True, timeout=10)
                if response.status_code == 200:
                    ext = os.path.splitext(src.split('?')[0])[1]
                    if not ext or len(ext) > 6:
                        ext = '.jpg'

                    # Extract and decode filename
                    raw_filename = os.path.splitext(os.path.basename(src.split('?')[0]))[0]
                    decoded_filename = unquote(raw_filename)  # ✅ Decode %28 to (
                    
                    # Remove any nested metadata (e.g., keep only the original filename in parentheses)
                    match = re.search(r'\(([^)]+)\)', decoded_filename)
                    if match:
                        orig_name_clean = match.group(1)
                    else:
                        # Fallback: clean hash suffix
                        orig_name_clean = re.sub(r'_[a-f0-9]{32}$', '', decoded_filename)

                    # Compose clean local filename
                    local_filename = f'website_{website_id}_page_{page_id}_({orig_name_clean})_{uuid.uuid4().hex}{ext}'
                    print(f"Downloading image from {src} to {local_filename}")

                    local_path = os.path.join(media_dir, 'websites', local_filename)
                    os.makedirs(os.path.dirname(local_path), exist_ok=True)

                    with open(local_path, 'wb') as f:
                        for chunk in response.iter_content(1024):
                            f.write(chunk)

                    # Update the tag's src to local media path
                    tag['src'] = f'/media/websites/{local_filename}'

            except Exception as e:
                continue

        # Convert <input type="image"> to <img>
        if tag.name == 'input' and tag.get('type') == 'image':
            new_img = soup.new_tag('img')
            # Copy src, alt, style, width, height, class, id
            for attr in ['src', 'alt', 'style', 'width', 'height', 'class', 'id']:
                if tag.has_attr(attr):
                    new_img[attr] = tag[attr]
            tag.replace_with(new_img)

    return str(soup)

def hex_to_rgba(hex_color, alpha=0.5):
    hex_color = hex_color.lstrip('#')
    lv = len(hex_color)
    if lv == 6:
        rgb = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    elif lv == 3:
        rgb = tuple(int(hex_color[i]*2, 16) for i in range(3))
    else:
        return f'rgba(20, 128, 138, {alpha})'  # fallback
    return f'rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, {alpha})'



