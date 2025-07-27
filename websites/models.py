from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from ckeditor.fields import RichTextField

MENU_TYPE_CHOICES = [
    ('header', 'Header Menu'),
    ('footer', 'Footer Menu'),
]

class Author(models.Model):
    name = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='authors/', blank=True, null=True)
    description = models.TextField(blank=True)
    image = models.TextField(blank=True)
    url = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.name

class Website(models.Model):
    name = models.CharField(max_length=100)
    domain = models.CharField(max_length=100)
    phone_number_display = models.CharField(max_length=100, help_text='Visible text for phone number')
    phone_number_link = models.CharField(max_length=30, help_text='Actual phone number for tel: link (with country code)')
    robots_txt = models.TextField(blank=True ,default='User-agent: *\nAllow: /' )
    github_repo = models.URLField(blank=True)
    is_public_repo = models.BooleanField(default=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    logo = models.ImageField(upload_to='websites/', blank=True, null=True)
    favicon = models.ImageField(upload_to='websites/', blank=True, null=True)
    heading_background_image = models.ImageField(upload_to='websites/', blank=True, null=True)
    footer_phone_cta = models.CharField(max_length=200, blank=True, null=True)
    footer_legal_disclaimer = models.TextField(blank=True, null=True)
    social_media_box = models.TextField(blank=True, null=True)
    google_search_console_tag = models.TextField(blank=True, null=True)
    google_tag = models.TextField(blank=True, null=True)
    meta_facebook_pixel = models.TextField(blank=True, null=True)
    google_analytics = models.TextField(blank=True, null=True)
    form_cta1 = models.CharField(max_length=200, default='FREE INSTANT QUOTE!')
    form_cta2 = models.CharField(max_length=200, default='*plus FREE bonus coupon*')
    form_question1 = models.CharField(max_length=200, default='What service do you need?')
    form_question2 = models.CharField(max_length=200, default='How many square feet?')
    form_options1 = models.TextField(blank=True, null=True ,default='page1\npage2\npage3')
    form_options2 = models.TextField(blank=True, null=True, default='Less than 300\nBetween 300-500\nMore than 500')
    form_quote_button = models.CharField(max_length=100, default='Get Quote!')
    form_name_label = models.CharField(max_length=100, default='Name')
    form_phone_label = models.CharField(max_length=100, default='Phone Number')
    form_email_label = models.CharField(max_length=100, default='Email')
    global_schema_default = '''{ "@context": "https://schema.org", "@type": "LocalBusiness", "name": "[Your Business Name]", "url": "[Your Website URL]", "telephone": "[Your Single Phone Number]", "priceRange": "[e.g., $$ or a description like 'Affordable', 'Competitive Pricing']", "image": "https://www.quora.com/ ##Can-you-explain-the-differences-between-a-brand-an-image-a-logo-and-a-symbol", "description": "[A brief description of your business and services]", "address": { "@type": "PostalAddress", "streetAddress": "[Your Street Address - even if clients don't visit, this is for Google's understanding of your base]", "addressLocality": "[Your Main City]", "addressRegion": "[Your State/Province]", "postalCode": "[Your Postal Code]", "addressCountry": "[Your Country]" }, "openingHoursSpecification": { "@type": "OpeningHoursSpecification", "dayOfWeek": [ "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday" ], "opens": "[Your Opening Time, e.g., 09:00]", "closes": "[Your Closing Time, e.g., 17:00]" }, "areaServed": [ { "@type": "State", "name": "[Your State/Province]" }, { "@type": "City", "name": "[Your Main City]" }, { "@type": "City", "name": "[Surrounding City 1]" }, { "@type": "City", "name": "[Surrounding City 2]" } ] }'''
    global_seo_schema = models.TextField(blank=True, null=True, default=global_schema_default, help_text='Global SEO schema (JSON-LD or other) to be included on every page.')
    header_box_color = models.CharField(max_length=32, default='#14808a', help_text='Header Text Background Box color (CSS hex)')
    phone_banner_bg_color = models.CharField(max_length=32, default='#174d78', help_text='Phone banner background color (CSS hex)')
    contact_box_color = models.CharField(max_length=32, default='#1e3a8a', help_text='Contact Box color (CSS hex)')
    author = models.OneToOneField('Author', on_delete=models.SET_NULL, null=True, blank=True, related_name='website')

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.domain:
            self.domain = slugify(self.name)
        super().save(*args, **kwargs)

class Page(models.Model):
    website = models.ForeignKey(Website, on_delete=models.CASCADE, related_name='pages')
    title = models.CharField(max_length=100)
    content = RichTextField()
    slug = models.CharField(max_length=100)
    is_homepage = models.BooleanField(default=False)
    nofollow_document = models.BooleanField(default=False, help_text='If True, all links to this page will have rel="nofollow".')
    meta_description = models.TextField(max_length=160, blank=True, null=True, help_text='SEO meta description (max 160 characters)')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    date_published = models.DateTimeField(null=True, blank=True, help_text='Date when the page was published')
    date_modified = models.DateTimeField(null=True, blank=True, help_text='Date when the page was last modified')
    breadcrumb = models.JSONField(editable=False, null=True, blank=True)  # auto-generated, not user-editable

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Page.objects.filter(website=self.website, slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        # Auto-generate breadcrumb
        self.breadcrumb = self.generate_breadcrumb()
        super().save(*args, **kwargs)

    def generate_breadcrumb(self):
        # Returns a list of dicts: [{title, url, exists}]
        parts = self.slug.strip('/').split('/') if self.slug else []
        breadcrumbs = [{'title': 'Domain', 'url': '/', 'exists': True}]
        current_slug = ''
        for part in parts:
            current_slug = f"{current_slug}/{part}" if current_slug else part
            exists = Page.objects.filter(website=self.website, slug=current_slug).exists()
            breadcrumbs.append({
                'title': part.capitalize(),
                'url': f"/{current_slug}/",
                'exists': exists
            })
        return breadcrumbs

    class Meta:
        unique_together = ('website', 'slug')

class Menu(models.Model):
    website = models.ForeignKey(Website, on_delete=models.CASCADE, related_name='menus')
    type = models.CharField(max_length=10, choices=MENU_TYPE_CHOICES)
    content = models.TextField(help_text='Enter menu in markdown format. Use tabs for submenus.')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('website', 'type')

    def __str__(self):
        return f"{self.website.name} - {self.get_type_display()}"

