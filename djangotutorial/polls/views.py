from django.db.models import F
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views import generic

from .models import Choice, Question
from django.utils import timezone

import os
from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=os.getenv(OPENAI_API_KEY))


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

def search(request):
    """Chat-style search page returning results as cards."""
    # from django.shortcuts import redirect
    # if request.GET.get("clear"):
    #     request.session.pop("chat_messages", None)
    #     # redirect back to /polls/search/ without any query or clear flag
    #     return redirect("polls:search")
    
    # Load or init chat history
    messages = request.session.get("chat_messages", [])

    api_history = [
            m for m in messages
            if m.get("role") in ("system", "user", "assistant")
            and "content" in m
        ]

    query = request.GET.get("q", "").strip()
    if query:
        # 1) Add the user’s query
        messages.append({
            "role": "user",
            "content": query
        })

        # 2) Send to OpenAI
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=api_history,
            max_tokens=200,
            temperature=0.7,
        )

        # 3) Append the assistant’s reply
        assistant_msg = response.choices[0].message
        messages.append({
            "role": assistant_msg.role,      # will be "assistant"
            "content": assistant_msg.content
        })

        # Persist history before building cards
        request.session["chat_messages"] = messages
        request.session.modified = True

        # 4) Build your own search cards (for UI only)
        cards = []
        for q in Question.objects.filter(question_text__icontains=query)[:5]:
            cards.append({
                "title": q.question_text,
                "description": f"Result related to '{q.question_text}'.",
                "image": "polls/images/images.jpeg",
                "video": "https://www.w3schools.com/html/mov_bbb.mp4",
            })

        # 5) If cards exist, append them as an assistant message
        if cards:
            messages.append({
                "role": "assistant",
                "cards": cards
            })
        else:
            messages.append({
                "role": "assistant",
                "content": "No results found."
            })

        # Save again
        request.session["chat_messages"] = messages
        request.session.modified = True

    return render(request, "polls/search.html", {
        "messages": messages
    })