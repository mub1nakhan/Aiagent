import json

from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from .models import MoodRequest
from .services import generate_solution, update_weekly_insight


@require_http_methods(["GET"])
@login_required
def index(request):
    history = (
        MoodRequest.objects.filter(user=request.user)
        .order_by("-created_at")[:10]
    )
    insights = (
        request.user.insights.all()[:3]
        if hasattr(request.user, "insights")
        else []
    )
    return render(
        request,
        "main/index.html",
        {"history": history, "insights": insights},
    )


@require_http_methods(["POST"])
@login_required
def solve_api(request):
    if request.content_type == "application/json":
        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return JsonResponse(
                {"ok": False, "errors": {"problem": "JSON formatini tekshiring."}},
                status=400,
            )
    else:
        payload = request.POST

    problem_text = (payload.get("problem") or "").strip()
    mood = (payload.get("mood") or "").strip().lower()
    title = (payload.get("title") or "").strip()
    tags = (payload.get("tags") or "").strip()
    try:
        intensity = int(payload.get("intensity") or 3)
    except (TypeError, ValueError):
        intensity = 3
    intensity = max(1, min(intensity, 5))

    allowed_moods = {choice[0] for choice in MoodRequest.MOOD_CHOICES}
    errors = {}

    if not problem_text:
        errors["problem"] = "Muammo matnini kiriting."
    if mood not in allowed_moods:
        errors["mood"] = "Mood tanlang."

    if errors:
        return JsonResponse({"ok": False, "errors": errors}, status=400)

    try:
        solution = generate_solution(
            problem_text=problem_text,
            mood=mood,
            title=title,
            tags=tags,
            intensity=intensity,
        )
    except RuntimeError as exc:
        if str(exc) == "OPENAI_UNAVAILABLE":
            return JsonResponse(
                {"ok": False, "errors": {"openai": "OpenAI API key topilmadi yoki SDK yo'q."}},
                status=500,
            )
        return JsonResponse(
            {"ok": False, "errors": {"openai": "OpenAI javobini qayta ishlashda xatolik."}},
            status=500,
        )

    record = MoodRequest.objects.create(
        user=request.user,
        title=title,
        problem_text=problem_text,
        mood=mood,
        intensity=intensity,
        tags=",".join(solution.tags) if solution.tags else tags,
        response_text=solution.response_text,
        emoji=solution.emoji,
        action_prompt=solution.action_prompt,
        model_used=solution.model_used,
        source=solution.source,
    )

    for index, step in enumerate(solution.steps, start=1):
        if step:
            record.steps.create(order=index, text=step)

    update_weekly_insight(request.user)

    return JsonResponse(
        {
            "ok": True,
            "id": record.id,
            "response_text": solution.response_text,
            "emoji": solution.emoji,
            "action_prompt": solution.action_prompt,
            "steps": solution.steps,
            "tags": solution.tags,
        }
    )


@require_http_methods(["GET", "POST"])
def register(request):
    if request.user.is_authenticated:
        return redirect("home")

    form = UserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect(reverse("login"))

    return render(request, "registration/register.html", {"form": form})
