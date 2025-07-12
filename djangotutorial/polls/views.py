from django.db.models import F
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views import generic

from .models import Choice, Question
from django.utils import timezone

from django.templatetags.static import static
from django.conf import settings

import os
from openai import OpenAI

os.environ.setdefault("HTTP_PROXY", "socks5://127.0.0.1:1080")
os.environ.setdefault("HTTPS_PROXY", "socks5://127.0.0.1:1080")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI(
    api_key=OPENAI_API_KEY,
    client_options={
        "proxies": "socks5h://ss-local:1080"
    },
)


class IndexView(generic.ListView):
    template_name = "polls/index.html"
    context_object_name = "latest_question_list"

    def get_queryset(self):
        """Return the last five published questions (excluding future ones)."""
        return (
            Question.objects
            .filter(pub_date__lte=timezone.now())
            .order_by("-pub_date")[:5]
        )


class DetailView(generic.DetailView):
    model = Question
    template_name = "polls/detail.html"

    def get_queryset(self):
        """Exclude questions with a publication date in the future."""
        return Question.objects.filter(pub_date__lte=timezone.now())


class ResultsView(generic.DetailView):
    model = Question
    template_name = "polls/results.html"

def vote(request, question_id):
    question = get_object_or_404(Question, pk=question_id)
    try:
        selected_choice = question.choice_set.get(pk=request.POST["choice"])
    except (KeyError, Choice.DoesNotExist):
        # Redisplay the question voting form.
        return render(
            request,
            "polls/detail.html",
            {
                "question": question,
                "error_message": "You didn't select a choice.",
            },
        )
    else:
        selected_choice.votes = F("votes") + 1
        selected_choice.save()
        # Always return an HttpResponseRedirect after successfully dealing
        # with POST data. This prevents data from being posted twice if a
        # user hits the Back button.
        return HttpResponseRedirect(reverse("polls:results", args=(question.id,)))

def media_proxy(request, path):
    import requests
    from django.conf import settings
    from django.http import StreamingHttpResponse, Http404
    """
    Proxy /media-proxy/<path> → http://127.0.0.1:9000/static/<path>
    supporting byte ranges so HTML5 <video> will stream.
    """
    upstream = f'http://127.0.0.1:9000/static/{path}'
    headers = {}
    # Forward Range headers for seeking
    if 'HTTP_RANGE' in request.META:
        headers['Range'] = request.META['HTTP_RANGE']

    resp = requests.get(upstream, headers=headers, stream=True)
    if resp.status_code not in (200, 206):
        raise Http404(f"Upstream returned {resp.status_code}")

    # Copy relevant headers into our response
    proxy_resp = StreamingHttpResponse(
        resp.iter_content(chunk_size=8192),
        status=resp.status_code,
        content_type=resp.headers.get('Content-Type', 'application/octet-stream')
    )
    for h in ('Content-Length', 'Content-Range', 'Accept-Ranges'):
        if h in resp.headers:
            proxy_resp[h] = resp.headers[h]

    return proxy_resp

def search(request):
    import logging
    logger = logging.getLogger(__name__)

    api_key = os.getenv("OPENAI_API_KEY")
    logger.debug(f"OpenAI key is present: {bool(api_key)}")

    messages = request.session.get("chat_messages", [])

    query = request.GET.get("q", "").strip()
    if query:
        messages.append({
            "role": "user",
            "content": query
        })
        
        api_history = [
            m for m in messages
            if m.get("role") in ("system", "user", "assistant")
            and "content" in m
        ]

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=api_history,
            max_tokens=200,
            temperature=0.7,
        )

        assistant_msg = response.choices[0].message
        messages.append({
            "role": assistant_msg.role,
            "content": assistant_msg.content
        })

        request.session["chat_messages"] = messages
        request.session.modified = True

        base = settings.MEDIA_BASE_URL.rstrip("/") + "/"
        
        cards = [
            {
                "title": q.question_text,
                "description": f"Result related to '{q.question_text}'.",
                "image": base + f"DB/{q.question_text}.jpeg",
                "video": base + f"DB/{q.question_text}.mp4",
            }
            for q in Question.objects.filter(question_text__icontains=query)[:5]
        ]

        if cards:
            messages.append({
                "role": "assistant",
                "cards": cards
            })

        request.session["chat_messages"] = messages
        request.session.modified = True

    return render(request, "polls/search.html", {
        "messages": messages
    })