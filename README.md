# Local Web Template - Django Site Creator

A comprehensive Django application for creating and managing static websites with customizable themes, SEO optimization, and GitHub integration.

## 🚀 Features

### Core Functionality
- **User Authentication**: Secure login/signup with Django AllAuth
- **Website Management**: Create, edit, and manage multiple websites
- **Page Management**: Rich text editor with CKEditor for content creation
- **SEO Optimization**: Meta descriptions, schema markup, and breadcrumbs
- **Static Site Export**: Generate complete static websites
- **GitHub Integration**: Direct deployment to GitHub repositories

### Design & Customization
- **Responsive Templates**: Bootstrap 5 based responsive design
- **Custom Branding**: Logo, favicon, and background image support
- **Color Customization**: Header, contact box, and phone banner colors
- **Menu Management**: Header and footer menu customization
- **Form Integration**: Customizable contact forms with CTA buttons

### SEO & Analytics
- **Schema Markup**: JSON-LD structured data support
- **Meta Tags**: Custom meta descriptions and titles
- **Sitemap Generation**: Automatic XML sitemap creation
- **Robots.txt**: Customizable search engine directives
- **Analytics Integration**: Google Analytics, Google Tag Manager, Facebook Pixel
- **Search Console**: Google Search Console verification

### Content Management
- **Rich Text Editor**: CKEditor with image upload support
- **Media Management**: Cloudinary integration for file storage
- **Author Profiles**: Author information and bio management
- **Breadcrumb Navigation**: Automatic breadcrumb generation
- **Nofollow Support**: SEO link attribute management

## 🛠️ Technology Stack

- **Backend**: Django 5.0.2
- **Frontend**: Bootstrap 5, Crispy Forms
- **Database**: SQLite (development), PostgreSQL (production ready)
- **Rich Text**: CKEditor 6.1.0
- **Authentication**: Django AllAuth
- **File Storage**: Cloudinary
- **Version Control**: GitPython for GitHub integration
- **Deployment**: Gunicorn ready

## 📋 Prerequisites

- Python 3.8+
- pip
- Git
- Cloudinary account (for media storage)
- GitHub account (for repository integration)

## 🚀 Installation & Setup

### 1. Clone the Repository
```bash
git clone <repository-url>
cd local_web_template
```

### 2. Create Virtual Environment
```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Configuration
Create a `.env` file in the project root with the following variables:

```env
# Django Settings
SECRET_KEY=your_django_secret_key_here
DEBUG=True

# GitHub Integration
GITHUB_TOKEN=your_github_personal_access_token

# Cloudinary Configuration
CLOUDINARY_CLOUD_NAME=your_cloudinary_cloud_name
CLOUDINARY_API_KEY=your_cloudinary_api_key
CLOUDINARY_API_SECRET=your_cloudinary_api_secret

# Database (Optional - for production)
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
```

### Required Environment Variables

| Variable Name | Description | Required | Example |
|---------------|-------------|----------|---------|
| `SECRET_KEY` | Django secret key for security | ✅ Yes | `django-insecure-your-secret-key-here` |
| `DEBUG` | Enable/disable debug mode | ✅ Yes | `True` (dev) / `False` (prod) |
| `GITHUB_TOKEN` | GitHub personal access token for repo integration | ✅ Yes | `ghp_xxxxxxxxxxxxxxxxxxxx` |
| `CLOUDINARY_CLOUD_NAME` | Cloudinary cloud name for media storage | ✅ Yes | `your-cloud-name` |
| `CLOUDINARY_API_KEY` | Cloudinary API key | ✅ Yes | `123456789012345` |
| `CLOUDINARY_API_SECRET` | Cloudinary API secret | ✅ Yes | `abcdefghijklmnopqrstuvwxyz` |
| `DATABASE_URL` | Database connection string (production) | ❌ No | `postgresql://user:pass@localhost:5432/db` |

### 5. Database Setup
```bash
python manage.py migrate
```

### 6. Create Superuser
```bash
python manage.py createsuperuser
```

### 7. Run Development Server
```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000` to access the application.

## 📁 Project Structure

```
local_web_template/
├── site_creator/          # Main Django project
│   ├── settings.py       # Project settings
│   ├── urls.py          # Main URL configuration
│   └── wsgi.py          # WSGI application
├── websites/             # Main application
│   ├── models.py        # Database models
│   ├── views.py         # View logic
│   ├── urls.py          # App URL patterns
│   └── forms.py         # Form definitions
├── templates/            # HTML templates
│   ├── base.html        # Base template
│   └── websites/        # Website-specific templates
├── media/               # User-uploaded files
├── staticfiles/         # Collected static files
└── requirements.txt     # Python dependencies
```

## 🎯 Usage Guide

### 1. User Registration & Login
- Visit the application and click "Sign Up"
- Verify your email address
- Log in to access the dashboard

### 2. Creating a Website
1. Click "Create New Website" on the dashboard
2. Fill in basic information:
   - Website name
   - Domain (auto-generated from name)
   - Phone numbers (display and link versions)
   - Logo and favicon (optional)

### 3. Managing Pages
1. Navigate to "Manage Pages" for your website
2. Create new pages with:
   - Title and content (using rich text editor)
   - SEO meta description
   - Slug (auto-generated)
   - Homepage designation

### 4. Customizing Appearance
- **Site Settings**: Configure colors, contact information, and branding
- **Menus**: Edit header and footer navigation
- **Author Profile**: Add author information and bio
- **Tracking**: Configure analytics and tracking codes

### 5. SEO Optimization
- **Meta Descriptions**: Add custom meta descriptions for each page
- **Schema Markup**: Configure JSON-LD structured data
- **Sitemap**: Automatic XML sitemap generation
- **Robots.txt**: Customize search engine directives

### 6. Export & Deployment
- **Static Export**: Download complete static website
- **GitHub Integration**: Deploy directly to GitHub repository
- **Custom Domain**: Configure custom domain settings

## 🔧 Configuration Options

### Website Settings
- **Colors**: Header box, phone banner, contact box colors
- **Contact Information**: Phone numbers, email, address
- **Social Media**: Social media links and sharing
- **Analytics**: Google Analytics, Tag Manager, Facebook Pixel
- **Forms**: Custom contact form configuration

### Content Tags
Use these special tags in your content:
- `[phone_1]` - Displays the primary phone number
- `[phone_2]` - Displays the secondary phone number
- `[sign_up_form]` - Inserts the contact form
- `[author_info]` - Displays author information

## 🚀 Deployment

### Development
```bash
python manage.py runserver
```

### Production
1. Set `DEBUG=False` in settings
2. Configure production database
3. Set up static file serving
4. Use Gunicorn as WSGI server

```bash
gunicorn site_creator.wsgi:application
```

### Environment Variables for Production
```env
DEBUG=False
SECRET_KEY=your_production_secret_key
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
```

## 🔒 Security Features

- CSRF protection enabled
- Secure session management
- Input validation and sanitization
- File upload security
- XSS protection headers

## 📊 Database Models

### Website
- Basic information (name, domain, phone numbers)
- Branding (logo, favicon, background images)
- SEO settings (meta tags, schema markup)
- Analytics configuration
- Form settings

### Page
- Content management with rich text editor
- SEO optimization (meta descriptions, slugs)
- Breadcrumb navigation
- Publication dates
- Nofollow link attributes

### Author
- Author profile information
- Bio and description
- Profile image and logo
- Contact information

### Menu
- Header and footer navigation
- Markdown-based menu configuration
- Submenu support

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue on GitHub
- Check the documentation
- Review the code comments

## 🔄 Updates & Maintenance

- Regular security updates for Django and dependencies
- Database migrations for new features
- Backup recommendations for production data
- Performance optimization guidelines

---

**Note**: This application is designed for creating local business websites with SEO optimization and modern web standards. It provides a comprehensive solution for small businesses to establish their online presence quickly and effectively. 