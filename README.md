# Static Site Creator

A Django application for creating and managing static websites with common themes.

## Features

- User authentication and registration
- Website creation and management
- GitHub integration for repository management
- Static site export functionality
- Common theme management
- Phone number replacement
- Sign-up form insertion
- Sitemap generation
- Robots.txt management

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
Create a `.env` file with:
```
SECRET_KEY=your_secret_key
GITHUB_TOKEN=your_github_token
```

4. Run migrations:
```bash
python manage.py migrate
```

5. Create a superuser:
```bash
python manage.py createsuperuser
```

6. Run the development server:
```bash
python manage.py runserver
```

## Usage

1. Register/Login to the application
2. Create a new website or manage existing ones
3. Customize content while maintaining the common theme
4. Export the site or deploy directly to GitHub
5. Use special tags in content:
   - [phone_1] for phone number
   - [sign_up_form] for sign-up form insertion 