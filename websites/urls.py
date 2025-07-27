from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('create/', views.create_website, name='create_website'),
    path('edit/<int:website_id>/', views.edit_website, name='edit_website'),
    path('pages/<int:website_id>/', views.manage_pages, name='manage_pages'),
    path('pages/<int:website_id>/create/', views.create_page, name='create_page'),
    path('pages/<int:website_id>/edit/<int:page_id>/', views.edit_page, name='edit_page'),
    path('export/<int:website_id>/', views.export_website, name='export_website'),
    path('github/<int:website_id>/', views.github_integration, name='github_integration'),
    path('website/<int:website_id>/export/', views.export_website, name='export_website'),
    path('website/<int:website_id>/delete/', views.delete_website, name='delete_website'),
    path('website/<int:website_id>/page/<int:page_id>/delete/', views.delete_page, name='delete_page'),
    path('website/<int:website_id>/page/<slug:slug>/', views.Page, name='view_page'),
    path('<int:website_id>/edit-menus/', views.edit_menus, name='edit_menus'),
    path('settings/<int:website_id>/', views.edit_site_settings, name='edit_site_settings'),
    path('settings/<int:website_id>/tracking/', views.tracking_settings, name='tracking_settings'),
    path('settings/<int:website_id>/form/', views.form_settings, name='form_settings'),
    path('settings/<int:website_id>/author/', views.edit_author, name='edit_author'),
] 