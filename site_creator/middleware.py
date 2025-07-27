import os
from django.http import HttpResponse

class CacheHeadersMiddleware:
    """
    Middleware to add cache headers for static and media files
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Add cache headers for static files
        if request.path.startswith('/static/'):
            response['Cache-Control'] = 'public, max-age=31536000'  # 1 year
            response['Expires'] = 'Thu, 31 Dec 2024 23:59:59 GMT'
        
        # Add cache headers for media files (images, etc.)
        elif request.path.startswith('/media/'):
            # Check if it's an image file
            if any(request.path.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']):
                response['Cache-Control'] = 'public, max-age=31536000'  # 1 year
                response['Expires'] = 'Thu, 31 Dec 2024 23:59:59 GMT'
            else:
                # For other media files, cache for 1 week
                response['Cache-Control'] = 'public, max-age=604800'  # 1 week
                response['Expires'] = 'Thu, 24 Dec 2024 23:59:59 GMT'
        
        return response 