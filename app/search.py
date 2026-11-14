"""LangSearch-backed venue discovery with MongoDB caching."""

from hashlib import sha256
from datetime import datetime, timedelta, timezone
import os

import httpx

from .service import now


SEARCH_URL = 'https://api.langsearch.com/v1/web-search'
CACHE_TTL = timedelta(hours=1)


def _cache_id(query: str) -> str:
    return 'langsearch-' + sha256(query.encode('utf-8')).hexdigest()


def search_venues(data: dict, query: str) -> dict:
    """Search current web results, cache them, and expose them as candidate venues."""
    query = ' '.join(query.split())
    if not query or len(query) > 500:
        raise ValueError('Search query must be between 1 and 500 characters')

    data.setdefault('searchCache', [])
    cache_id = _cache_id(query.lower())
    cached = next((row for row in data['searchCache'] if row['id'] == cache_id), None)
    if cached:
        searched_at = datetime.fromisoformat(cached['searched_at'])
        if datetime.now(timezone.utc) - searched_at < CACHE_TTL:
            return {'query': query, 'cached': True, 'results': cached['results']}

    api_key = os.getenv('LANGSEARCH_API_KEY')
    if not api_key:
        raise ValueError('LangSearch is not configured')

    response = httpx.post(
        os.getenv('LANGSEARCH_URL', SEARCH_URL),
        headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
        json={'query': query, 'count': 5, 'contents': {'text': {'max_characters': 2500}}},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if str(payload.get('code')) != '200':
        raise ValueError(f"LangSearch failed: {payload.get('message', 'Unknown error')}")

    results = []
    for page in payload.get('data', {}).get('webPages', {}).get('value', [])[:5]:
        url = page.get('url')
        if not url:
            continue
        venue_id = 'venue-' + sha256(url.encode('utf-8')).hexdigest()[:24]
        if not any(v['id'] == venue_id for v in data['venues']):
            data['venues'].append({
                'id': venue_id,
                'name': page.get('name', 'Web search result')[:200],
                'facts': [],
                'tags': [],
                'source': url,
                'demo': False,
            })
        results.append({
            'venue_id': venue_id,
            'name': page.get('name', 'Web search result')[:200],
            'url': url,
            'text': (page.get('text') or page.get('snippet') or '')[:2500],
            'datePublished': page.get('datePublished'),
        })

    record = {'id': cache_id, 'query': query, 'results': results, 'searched_at': now()}
    data['searchCache'] = [row for row in data['searchCache'] if row['id'] != cache_id]
    data['searchCache'].append(record)
    return {'query': query, 'cached': False, 'results': results}
