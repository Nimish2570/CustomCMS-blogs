from django import forms
from .models import Website, Page, Menu, Author
from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django.utils.text import slugify
import re
from django.forms import formset_factory, BaseFormSet
import json

class WebsiteForm(forms.ModelForm):
    class Meta:
        model = Website
        fields = ['domain']
        # Removed: 'name', 'phone_number_display', 'robots_txt', 'github_repo', 'is_public_repo'
        # Add any other fields you want to keep for creation
        widgets = {
            # 'robots_txt': forms.Textarea(attrs={'rows': 4}),
        }

class PageForm(forms.ModelForm):
    # Reorder fields: title, slug, content, is_homepage
    title = forms.CharField()
    slug = forms.CharField(
        required=False,
        widget=forms.TextInput(),
       
    )
    content = forms.CharField(widget=CKEditorUploadingWidget(config_name='default', attrs={'class': 'ckeditor'}))
    meta_description = forms.CharField(
        max_length=160,
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Enter a brief description of this page for search engines (max 160 characters)'}),
        help_text='SEO meta description that appears in search results (max 160 characters)'
    )
    is_homepage = forms.BooleanField(required=False)
    nofollow_document = forms.BooleanField(required=False, label='Nofollow Document', help_text='If checked, all links to this page will have rel="nofollow".')
    date_published = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control', 'placeholder': 'YYYY-MM-DDThh:mm', 'data-today-btn': 'true'}),
        help_text='Date when the page was published (optional).'
    )
    date_modified = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control', 'placeholder': 'YYYY-MM-DDThh:mm', 'data-today-btn': 'true'}),
        help_text='Date when the page was last modified (optional).'
    )

    class Meta:
        model = Page
        fields = ['title', 'slug', 'content', 'meta_description', 'is_homepage', 'nofollow_document', 'date_published', 'date_modified']

    def clean_slug(self):
        slug = self.cleaned_data.get('slug')
        title = self.cleaned_data.get('title')
        if not slug and title:
            slug = title
        if slug:
            slug = slug.lower()
            slug = slug.replace(' ', '-')
            slug = re.sub(r'[^a-z0-9\-/]', '', slug)
            slug = re.sub(r'-+', '-', slug)
            slug = re.sub(r'/+', '/', slug)
            slug = '/'.join(segment.strip('-') for segment in slug.split('/'))
            slug = '/'.join(filter(None, slug.split('/')))
            slug = f'{slug}' if slug else '/'
        else:
            slug = '/'
        slug = re.sub(r'/+', '/', slug)
        base_slug = slug
        counter = 1
        website = self.instance.website if self.instance.pk else self.initial.get('website')
        if website:
            while Page.objects.filter(website=website, slug=slug).exclude(pk=self.instance.pk).exists():
                slug = re.sub(r'/$', '', base_slug) + f'-{counter}/'
                counter += 1
        return slug

class GitHubRepoForm(forms.Form):
    repo_name = forms.CharField(
        max_length=200, 
        required=False,
        label="Repo name*",
        help_text="Enter a new repository name to create a new repository"
    )
    existing_repo = forms.ChoiceField(
        required=False, 
        label="Existing repo",
        help_text="Or select an existing repository from the dropdown"
    )

    def __init__(self, *args, **kwargs):
        repos = kwargs.pop('repos', [])
        self.connected_repo = kwargs.pop('connected_repo', None)
        super().__init__(*args, **kwargs)
        self.fields['existing_repo'].choices = [('', '-- Select Repository --')] + [(repo, repo) for repo in repos]

    def clean(self):
        cleaned_data = super().clean()
        repo_name = cleaned_data.get('repo_name')
        existing_repo = cleaned_data.get('existing_repo')
        
        # If existing repo is selected, use that instead of repo_name
        if existing_repo:
            cleaned_data['repo_name'] = existing_repo
            cleaned_data['existing_repo'] = existing_repo
        
        # Only require a repo name if no connected repo exists
        if not cleaned_data.get('repo_name') and not self.connected_repo:
            raise forms.ValidationError("Please either enter a new repository name or select an existing repository.")
        
        return cleaned_data

class MenuForm(forms.ModelForm):
    helper_links = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'readonly': 'readonly', 'rows': 6, 'style': 'background:#f9f9f9; font-family:monospace;'}),
        label='All Pages (Markdown Links)',
        help_text='Copy and paste these links into your menu as needed.'
    )

    class Meta:
        model = Menu
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 10, 'placeholder': 'Enter menu in markdown format. Use tabs for submenus.'}),
        }

    def __init__(self, *args, **kwargs):
        website = kwargs.pop('website', None)
        super().__init__(*args, **kwargs)
        if website:
            pages = website.pages.all()
            links = '\n'.join(f'[{p.title}]({p.slug})' for p in pages)
            self.fields['helper_links'].initial = links
            # Set default content if empty
            if not self.instance.content:
                if self.instance.type == 'header':
                    homepage = pages.filter(is_homepage=True).first()
                    homepage_slug = homepage.slug if homepage else None
                    services_links = '\n'.join(
                        f'\t[{p.title}]({p.slug})' for p in pages if p.slug != homepage_slug
                    )
                    self.initial['content'] = '[Homepage](/)\n[Services]()' + (f'\n{services_links}' if services_links else '') + '\n[Contact Us](/contact/)'
                elif self.instance.type == 'footer':
                    username = website.owner.username if hasattr(website, 'owner') else 'our company'
                    self.initial['content'] = f'This is a 3rd party website, we do not perform the work itself but are merely a marketing website for {username}.\n[Disclaimer](/disclaimer)\n[Privacy Policy](/privacy-policy)\n[Terms of Service](/terms-of-service)'
        else:
            self.fields['helper_links'].initial = 'No pages found.'

class SocialMediaLinkForm(forms.Form):
    label = forms.CharField(max_length=50, required=True, label='Platform')
    url = forms.URLField(required=True, label='Link')

class BaseSocialMediaFormSet(BaseFormSet):
    def clean(self):
        if any(self.errors):
            return
        # Optionally add custom validation here

class TrackingSettingsForm(forms.ModelForm):
    google_search_console_tag = forms.CharField(label='Google Search Console', required=False, widget=forms.Textarea(attrs={'rows': 2}))
    google_tag = forms.CharField(label='Google Tag Manager', required=False, widget=forms.Textarea(attrs={'rows': 2}))
    google_analytics = forms.CharField(label='Google Analytics', required=False, widget=forms.Textarea(attrs={'rows': 2}))
    meta_facebook_pixel = forms.CharField(label='Meta Pixel', required=False, widget=forms.Textarea(attrs={'rows': 2}))
    class Meta:
        model = Website
        fields = [
            'google_search_console_tag',
            'google_tag',
            'google_analytics',
            'meta_facebook_pixel',
        ]
        widgets = {
            'google_search_console_tag': forms.Textarea(attrs={'rows': 2}),
            'google_tag': forms.Textarea(attrs={'rows': 2}),
            'google_analytics': forms.Textarea(attrs={'rows': 2}),
            'meta_facebook_pixel': forms.Textarea(attrs={'rows': 2}),
        }

class FormSettingsForm(forms.ModelForm):
    class Meta:
        model = Website
        fields = [
            'form_cta1', 'form_cta2', 'form_question1', 'form_options1', 'form_question2', 'form_options2', 'form_quote_button',
            'form_name_label', 'form_phone_label', 'form_email_label',
        ]
        widgets = {
            'form_cta1': forms.TextInput(),
            'form_cta2': forms.TextInput(),
            'form_question1': forms.TextInput(),
            'form_options1': forms.Textarea(attrs={'rows': 2}),
            'form_question2': forms.TextInput(),
            'form_options2': forms.Textarea(attrs={'rows': 2}),
            'form_quote_button': forms.TextInput(),
            'form_name_label': forms.TextInput(),
            'form_phone_label': forms.TextInput(),
            'form_email_label': forms.TextInput(),
        }

class WebsiteSettingsForm(forms.ModelForm):
    phone_number_display = forms.CharField(label='Phone Number (Visible Text)', required=False)
    phone_number_link = forms.CharField(label='Phone Number Link (for tel:)', required=False)
    form_options1 = forms.CharField(
        label='Form Question 1 Options',
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Enter one option per line'})
    )
    form_options2 = forms.CharField(
        label='Form Question 2 Options',
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Enter one option per line'})
    )
    social_media_box = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 4, 'placeholder': '[INSTA](https://www.instagram.com/username/)\n[Twitter](https://www.x.com/username/)'}),
        label='Social Media Links',
        help_text='Enter one link per line in the format: [Label](URL)'
    )
    form_name_label = forms.CharField(label='Name Field Label', required=False)
    form_phone_label = forms.CharField(label='Phone Field Label', required=False)
    form_email_label = forms.CharField(label='Email Field Label', required=False)
    global_seo_schema = forms.CharField(
        label='Global SEO Schema',
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 16,
            'style': 'width:100%; min-width:100%; max-width:100%; font-family:monospace; font-size:15px; background:#f9f9f9; padding:12px; box-sizing:border-box; resize:vertical;'
        }),
        help_text='This schema will be included on every page.'
    )
    header_box_color = forms.CharField(
        label='Header Text Background Box',
        required=False,
        widget=forms.TextInput(attrs={'type': 'color'}),
        help_text=''
    )
    phone_banner_bg_color = forms.CharField(label='Phone Banner Background', required=False, widget=forms.TextInput(attrs={'type': 'color'}), help_text='CSS hex value for .phone-banner background')
    contact_box_color = forms.CharField(label='Contact Box Color', required=False, widget=forms.TextInput(attrs={'type': 'color'}), help_text='CSS hex value for .contact-form-container background')

    class Meta:
        model = Website
        fields = [
            'domain', 'phone_number_display', 'phone_number_link', 'logo', 'favicon', 'robots_txt', 'github_repo', 'is_public_repo',
            'heading_background_image', 'footer_phone_cta', 'footer_legal_disclaimer',
            'social_media_box',
            'global_seo_schema',
            'header_box_color', 'phone_banner_bg_color', 'contact_box_color',
        ]
        widgets = {
            'robots_txt': forms.Textarea(attrs={'rows': 4}),
            'footer_legal_disclaimer': forms.Textarea(attrs={'rows': 3}),
            'phone_number_display': forms.TextInput(),
            'phone_number_link': forms.TextInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Handle form_options1
        val1 = getattr(self.instance, 'form_options1', None)
        if not val1 or (isinstance(val1, str) and val1.strip() == ''):
            if self.instance and hasattr(self.instance, 'pages') and self.instance.pk:
                pages = self.instance.pages.all()
                non_homepage_titles = [p.title for p in pages if not p.is_homepage]
                self.fields['form_options1'].initial = '\n'.join(non_homepage_titles)
            else:
                self.fields['form_options1'].initial = ''
        else:
            self.fields['form_options1'].initial = val1
        # Handle form_options2
        val2 = getattr(self.instance, 'form_options2', None)
        if not val2 or (isinstance(val2, str) and val2.strip() == ''):
            self.fields['form_options2'].initial = 'Less than 300\nBetween 300-500\nMore than 500'
        else:
            self.fields['form_options2'].initial = val2
        # Prepare initial data for social media links as markdown
        raw_links = getattr(self.instance, 'social_media_box', []) or []
        social_links = []
        if isinstance(raw_links, str):
            # Try to parse as JSON
            try:
                social_links = json.loads(raw_links)
            except Exception:
                # Try to parse as [Label](URL) lines (allow spaces)
                for line in raw_links.splitlines():
                    m = re.match(r'^\[(.+?)\]\s*\((.+?)\s*\)$', line.strip())
                    if m:
                        label, url = m.groups()
                        social_links.append({'label': label.strip(), 'url': url.strip()})
        elif isinstance(raw_links, list):
            social_links = raw_links
        # Convert to markdown link format for textarea
        lines = []
        for link in social_links:
            if isinstance(link, dict) and 'label' in link and 'url' in link:
                lines.append(f'[{link["label"]}]({link["url"]})')
        self.fields['social_media_box'].initial = '\n'.join(lines)

    def clean_form_options1(self):
        data = self.cleaned_data['form_options1']
        return data.strip() if data else ''

    def clean_form_options2(self):
        data = self.cleaned_data['form_options2']
        return data.strip() if data else ''

    def clean_social_media_box(self):
        data = self.cleaned_data.get('social_media_box', '')
        lines = []
        import re
        for line in data.splitlines():
            line = line.strip()
            if not line:
                continue
            m = re.match(r'^\[(.+?)\]\s*\((.+?)\s*\)$', line)
            if m:
                label, url = m.groups()
                lines.append(f'[{label.strip()}]({url.strip()})')
            else:
                raise forms.ValidationError('Each line must be in the format: [Label](URL)')
        return '\n'.join(lines) 

class AuthorForm(forms.ModelForm):
    class Meta:
        model = Author
        fields = ['name', 'logo', 'description', 'image', 'url'] 