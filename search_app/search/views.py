import re
import os, httpx, openai
from .models import Anime
import requests
from mysite.const import *

from django.shortcuts import render, redirect
from django.db.models import Q
from django.http import JsonResponse
from django.http import StreamingHttpResponse, Http404
from urllib.parse import quote

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
http_client = httpx.Client(proxy=PROXY_FOR_OPENAI)
client = openai.OpenAI(api_key=OPENAI_API_KEY, http_client=http_client)


def media_proxy(request, path):
    safe = quote(path, safe='/') 
    upstream = f'{MEDIA_TUNNEL}/{safe}'
    headers = {}
    if 'HTTP_RANGE' in request.META:
        headers['Range'] = request.META['HTTP_RANGE']

    resp = requests.get(upstream, headers=headers, stream=True)
    if resp.status_code not in (200, 206):
        raise Http404(f'Upstream returned {resp.status_code}')

    proxy_resp = StreamingHttpResponse(
        resp.iter_content(chunk_size=8192),
        status=resp.status_code,
        content_type=resp.headers.get('Content-Type', 'application/octet-stream')
    )
    for h in ('Content-Length', 'Content-Range', 'Accept-Ranges'):
        if h in resp.headers:
            proxy_resp[h] = resp.headers[h]

    return proxy_resp


def suggestions(request):
    q = request.GET.get('q', '').strip()
    if not q:
        return JsonResponse([], safe=False)

    qs = Anime.objects.filter(name__icontains=q)[:NUMBER_OF_SUGGESTIONS]
    data = [
        {'id': obj.id, 'text': obj.name}
        for obj in qs
    ]
    return JsonResponse(data, safe=False)


def clear(request):
    request.session.pop('chat_messages', None)
    return redirect('search:search')


def search(request):
    history = request.session.get('chat_messages', [])

    system_context = {
        'role': 'system',
        'content': (
            'Твоя задача - рекомендовать аниме по запросу пользователя.'
            'Если ты понял что хочет пользователь, ответь в формате [title], и больше ничего не добавляй. Обязательно укажи title в квадратных скобках.'
            'Если не уверен, постарайся выяснить, что именно он хочет'
        )
    }

    query = request.GET.get('q', '').strip()
    if query:
        content_history = [m for m in history if m.get('content') is not None and m.get('role') != 'user_to_db']
        messages = [system_context] + content_history + [{'role':'user','content': query}]
        
        q_obj = Q()
        q_obj |= Q(name__icontains=query)
        anime = Anime.objects.filter(q_obj).first()

        if not anime:
            history.append({'role': 'user', 'content': query})

            response = client.responses.create(
                model='gpt-4.1',
                tools=[{'type': 'web_search_preview'}],
                input=messages,
            )

            assistant_content = response.output_text
            history.append({'role': 'assistant', 'content': assistant_content})

            m = re.search(r'\[([^\]]+)\]', assistant_content)
            anime = None
            if m:
                title = m.group(1)
                q_obj |= Q(name__icontains=title)
                anime = Anime.objects.filter(q_obj).first()

        if anime:
            history.append({'role': 'user_to_db', 'content': query})
            base = MEDIA_BASE_URL.rstrip('/') + '/'
            history.append({
                'role': 'assistant',
                'cards': [{
                    'title': anime.name,
                    'description': 'Here it is!',
                    'image': f'{base}DB/{anime.id}.jpg',
                    'video': f'{base}DB/{anime.id}/{anime.id}.mp4',
                }]
            })

        request.session['chat_messages'] = history
        request.session.modified = True

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'messages': history}, safe=False)
    return render(request, 'search/index.html', {'messages': history})
    