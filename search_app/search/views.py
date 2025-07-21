from __future__ import annotations

import os
import re
import sys
from typing import Any, Dict, List
from urllib.parse import quote

import httpx
import openai
import requests
from django.conf import settings
from django.db.models import Q
from django.http import (
    Http404,
    HttpRequest,
    HttpResponse,
    JsonResponse,
    StreamingHttpResponse,
)
from django.shortcuts import redirect, render

from .models import Anime, Choice, Question

OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4.1"
TOP_SUGGESTIONS = 5  # Кол‑во вариантов в автодополнении

if OPENAI_API_KEY is None:
    raise RuntimeError("OPENAI_API_KEY не найден в переменных окружения")

# Настраиваем прокси‑клиент в зависимости от ОС
HTTP_CLIENT = httpx.Client(
    proxy="socks5h://host.docker.internal:1080"
    if sys.platform == "darwin"
    else "socks5h://ss-local:1080"
)

openai_client = openai.OpenAI(api_key=OPENAI_API_KEY, http_client=HTTP_CLIENT)

def _build_media_url(*parts: str) -> str:
    """Формирует абсолютный URL до медиа‑файла."""
    base = settings.MEDIA_BASE_URL.rstrip("/")
    return "/".join([base, *map(str, parts)])


def _append_history(session: Dict[str, Any], message: Dict[str, Any]) -> None:
    """Добавляет сообщение к истории в сессии."""
    history: list = session.setdefault("chat_messages", [])
    history.append(message)
    session.modified = True


def _is_duplicate_card(history: List[dict], anime_id: str, episode: str) -> bool:
    """Проверяет, возвращалась ли уже та же карточка."""
    if not history:
        return False
    last = history[-1]
    card = (
        last.get("cards", [{}])[0]
        if last.get("role") == "assistant" and last.get("cards")
        else {}
    )
    return str(card.get("id")) == str(anime_id) and str(card.get("episode")) == str(
        episode
    )


def _assistant_card(anime: Anime, episode: int | str = 0) -> Dict[str, Any]:
    """Формирует карточку ассистента по данным аниме."""
    return {
        "role": "assistant",
        "cards": [
            {
                "id": anime.id,
                "title": anime.name,
                "episode": episode,
                "description": "Here it is!",
                "image": _build_media_url("DB", f"{anime.id}.jpg"),
                "video": _build_media_url("DB", str(anime.id), f"{anime.id}.mp4"),
            }
        ],
    }


def media_proxy(request: HttpRequest, path: str) -> StreamingHttpResponse:
    """
    Проксирует запрос к медиа‑контенту через другой сервис.
    Передаёт заголовок Range, чтобы работали seeking‑запросы.
    """
    safe = quote(path, safe="/")
    upstream = f"http://media-tunnel:8080/{safe}"

    headers = {}
    if "HTTP_RANGE" in request.META:
        headers["Range"] = request.META["HTTP_RANGE"]

    resp = requests.get(upstream, headers=headers, stream=True)

    if resp.status_code not in (200, 206):
        raise Http404(f"Upstream returned {resp.status_code}")

    proxy_resp = StreamingHttpResponse(
        resp.iter_content(chunk_size=8192),
        status=resp.status_code,
        content_type=resp.headers.get("Content-Type", "application/octet-stream"),
    )

    for header in ("Content-Length", "Content-Range", "Accept-Ranges"):
        if header in resp.headers:
            proxy_resp[header] = resp.headers[header]

    return proxy_resp


def suggestions(request: HttpRequest) -> JsonResponse:
    """
    Автодополнение названий аниме.
    Возвращает первые TOP_SUGGESTIONS совпадений.
    """
    q = request.GET.get("q", "").strip()
    if not q:
        return JsonResponse([], safe=False)

    queryset = Anime.objects.filter(name__icontains=q)[:TOP_SUGGESTIONS]
    data = [{"id": a.id, "text": a.name} for a in queryset]
    return JsonResponse(data, safe=False)


def clear_history(request: HttpRequest) -> HttpResponse:
    request.session.pop("chat_messages", None)
    request.session.modified = True
    return redirect("search")


def search(request: HttpRequest) -> HttpResponse:
    history: List[dict] = request.session.get("chat_messages", [])

    anime_id = request.GET.get("anime_id")
    episode = request.GET.get("episode")

    if anime_id and episode:
        try:
            anime = Anime.objects.get(id=anime_id)
        except Anime.DoesNotExist:
            anime = None

        if anime and not _is_duplicate_card(history, anime_id, episode):
            _append_history(request.session, _assistant_card(anime, episode))

    query = request.GET.get("q", "").strip()
    if query:
        system_context = {
            "role": "system",
            "content": (
                "Твоя задача — рекомендовать аниме по запросу пользователя. "
                "Если ты понял, что хочет пользователь, ответь в формате [title] "
                "и больше ничего не добавляй. Обязательно укажи title в квадратных скобках. "
                "Если не уверен — уточни детали."
            ),
        }

        # Берём только сообщения с текстом, исключая служебные user_to_db
        content_history = [
            m for m in history if m.get("content") and m.get("role") != "user_to_db"
        ]

        messages = [system_context, *content_history, {"role": "user", "content": query}]

        # Пробуем найти по базе напрямую
        anime = Anime.objects.filter(name__icontains=query).first()

        # Если не нашли — спрашиваем LLM
        if not anime:
            _append_history(request.session, {"role": "user", "content": query})

            response = openai_client.responses.create(
                model=OPENAI_MODEL,
                tools=[{"type": "web_search_preview"}],
                input=messages,
            )

            assistant_text = response.output_text
            _append_history(request.session, {"role": "assistant", "content": assistant_text})

            # Ищем [title] в ответе
            match = re.search(r"\[([^\]]+)]", assistant_text)
            if match:
                title = match.group(1)
                anime = Anime.objects.filter(name__icontains=title).first()

        if anime:
            _append_history(request.session, {"role": "user_to_db", "content": query})
            _append_history(request.session, _assistant_card(anime))

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"messages": request.session["chat_messages"]}, safe=False)

    return render(
        request, "polls/search.html", {"messages": request.session.get("chat_messages", [])}
    )
