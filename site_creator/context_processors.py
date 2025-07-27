def is_search_bot(request):
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    return {
        'is_search_bot': 'googlebot' in user_agent or 'bingbot' in user_agent
    } 