from django.contrib import admin
from .models import Website, Page, Menu, Author
from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django import forms
from .forms import MenuForm

class PageAdminForm(forms.ModelForm):
    content = forms.CharField(widget=CKEditorUploadingWidget())
    
    class Meta:
        model = Page
        fields = '__all__'

@admin.register(Website)
class WebsiteAdmin(admin.ModelAdmin):
    list_display = ('name', 'domain', 'owner', 'created_at', 'header_box_color', 'phone_banner_bg_color', 'contact_box_color')
    fields = ('name', 'domain', 'owner', 'logo', 'favicon', 'heading_background_image', 'robots_txt', 'github_repo', 'is_public_repo',
              'footer_phone_cta', 'footer_legal_disclaimer', 'social_media_box', 'google_search_console_tag', 'google_tag',
              'meta_facebook_pixel', 'google_analytics', 'form_cta1', 'form_cta2', 'form_question1', 'form_question2',
              'form_options1', 'form_options2', 'form_quote_button', 'form_name_label', 'form_phone_label', 'form_email_label',
              'global_seo_schema', 'header_box_color', 'phone_banner_bg_color', 'contact_box_color')
    search_fields = ('name', 'domain')
    list_filter = ('created_at',)

@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    form = PageAdminForm
    list_display = ('title', 'website', 'is_homepage', 'nofollow_document', 'created_at')
    list_filter = ('website', 'is_homepage', 'nofollow_document', 'created_at')
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}

class MenuAdmin(admin.ModelAdmin):
    form = MenuForm
    list_display = ('website', 'type', 'updated_at')
    list_filter = ('website', 'type')

admin.site.register(Menu, MenuAdmin)

@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('name', 'url')
    search_fields = ('name',)
