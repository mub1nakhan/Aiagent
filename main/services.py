import hashlib
import json
import os
import random
from dataclasses import dataclass

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

try:
    from openai import OpenAI

    _OPENAI_AVAILABLE = True
except Exception:
    OpenAI = None
    _OPENAI_AVAILABLE = False

from .models import MoodInsight, MoodRequest


@dataclass(frozen=True)
class MoodSolution:
    response_text: str
    emoji: str
    action_prompt: str
    steps: list[str]
    tags: list[str]
    source: str
    model_used: str


def _stable_rng(problem_text: str, mood: str) -> random.Random:
    seed_base = f"{problem_text}|{mood}".encode("utf-8")
    seed = int(hashlib.sha256(seed_base).hexdigest(), 16) % (2**32)
    return random.Random(seed)


def _generate_local_solution(problem_text: str, mood: str) -> MoodSolution:
    rng = _stable_rng(problem_text, mood)

    jokes = [
        "Bugun kichkina kulgi ham katta energiya beradi. Biz buni uddalaymiz!",
        "Sen qahramonsan, shunchaki hozir coffee break rejimidasan.",
        "Hamma narsa joyiga tushadi, faqat birinchi qadamni qo'yamiz.",
    ]
    motivational_quotes = [
        "Kichik qadamlar katta natijalarga olib boradi.",
        "Sabr va qat'iyat — eng kuchli kombo.",
        "Bugun qilganing ertangi g'alabaga sarmoya.",
    ]
    mini_tasks = [
        "1 ta kichik vazifani yozib, 10 daqiqada bajaring.",
        "Stol ustini tartibga keltiring va bitta faylni yopib qo'ying.",
        "2 daqiqa chuqur nafas olib, keyin bitta ishni boshlang.",
    ]

    tips = [
        "Eng muhim 1 ta ishni aniqlang va shuni birinchi qiling.",
        "Telefonni 25 daqiqa jim rejimga qo'ying.",
        "Kalendarni 30 daqiqalik bloklarga bo'ling.",
    ]
    micro_schedules = [
        "10 daqiqa reja + 25 daqiqa fokus + 5 daqiqa tanaffus.",
        "2 daqiqa tayyorgarlik + 20 daqiqa ish + 3 daqiqa review.",
        "15 daqiqa eng muhim vazifa + 5 daqiqa natija yozish.",
    ]

    energy_recovery = [
        "3 daqiqa yengil stretching qiling.",
        "Bir stakan suv iching va 2 daqiqa yuring.",
        "Ko'zlarni dam oldiring: 20-20-20 qoidasi.",
    ]
    focus_prompts = [
        "Hozir bitta eng kichik qadam nima?",
        "Agar 10 daqiqa vaqt bo'lsa, nimani tugatardingiz?",
        "Eng katta to'siqni 1 jumlada yozib chiqing.",
    ]

    if mood == "happy":
        response_text = rng.choice(jokes)
        emoji = rng.choice(["😊", "✨", "😁"])
        action_prompt = rng.choice(mini_tasks)
        steps = [
            "Kayfiyatingizni 1 jumlada yozing.",
            "Eng kichik vazifani 10 daqiqada boshlang.",
            "Natijani kichik g'alaba sifatida belgilang.",
        ]
        tags = ["positive", "light", "momentum"]
    elif mood == "stressed":
        response_text = rng.choice(tips)
        emoji = rng.choice(["🧘", "📌", "⏱️"])
        action_prompt = rng.choice(micro_schedules)
        steps = [
            "Bitta asosiy vazifani tanlang.",
            "25 daqiqa fokus blokini qo'ying.",
            "5 daqiqada natijani tekshiring.",
        ]
        tags = ["focus", "priority", "deadline"]
    elif mood == "tired":
        response_text = rng.choice(energy_recovery)
        emoji = rng.choice(["😴", "🫖", "🫧"])
        action_prompt = rng.choice(focus_prompts)
        steps = [
            "Suv iching va 2 daqiqa yuring.",
            "Eng kichik qadamni yozing.",
            "10 daqiqada bitta vazifani tugating.",
        ]
        tags = ["recharge", "gentle", "clarity"]
    elif mood == "motivated":
        response_text = rng.choice(motivational_quotes)
        emoji = rng.choice(["🔥", "🚀", "💪"])
        action_prompt = rng.choice(mini_tasks)
        steps = [
            "Bugun qilinadigan 3 vazifani yozing.",
            "Eng kattasini 30 daqiqalik blokka bo'ling.",
            "Progressni 1 jumlada belgilab qo'ying.",
        ]
        tags = ["drive", "execution", "progress"]
    else:
        response_text = "Kayfiyat aniqlanmadi. Keling, kichik qadamdan boshlaymiz."
        emoji = "🙂"
        action_prompt = "Muammoni 1 jumlada aniq yozing va 5 daqiqa ishlang."
        steps = [
            "Muammoni yozing.",
            "Bitta kichik qadamni tanlang.",
            "5 daqiqa vaqt belgilang.",
        ]
        tags = ["start", "clarity"]

    return MoodSolution(
        response_text=response_text,
        emoji=emoji,
        action_prompt=action_prompt,
        steps=steps,
        tags=tags,
        source="local",
        model_used="local",
    )


def generate_solution(
    problem_text: str,
    mood: str,
    title: str = "",
    tags: str = "",
    intensity: int = 3,
) -> MoodSolution:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not _OPENAI_AVAILABLE:
        if getattr(settings, "OPENAI_REQUIRED", True):
            raise RuntimeError("OPENAI_UNAVAILABLE")
        return _generate_local_solution(problem_text, mood)

    model_name = getattr(settings, "OPENAI_MODEL", "gpt-5.4-mini")
    instructions = (
        "Siz mood-based yordamchi siz. Vaziyatga mos, kontekstli yechim bering. "
        "Javobni faqat JSON formatida qaytaring. "
        "Kalitlar: response_text, emoji, action_prompt, steps, tags. "
        "response_text 2-4 jumla bo'lsin va muammo kontekstini aks ettirsin. "
        "emoji bitta bo'lsin. action_prompt 1 ta aniq qadam. "
        "steps 3 ta qisqa qadamdan iborat list bo'lsin. "
        "tags 2-4 ta qisqa teglar."
    )
    user_input = (
        f"Sarlavha: {title}\n"
        f"Muammo: {problem_text}\n"
        f"Mood: {mood}\n"
        f"Intensity: {intensity}/5\n"
        f"User tags: {tags}"
    )

    try:
        client = OpenAI()
        response = client.responses.create(
            model=model_name,
            input=[
                {"role": "developer", "content": instructions},
                {"role": "user", "content": user_input},
            ],
        )
        raw_text = response.output_text
        data = json.loads(raw_text)
        response_text = str(data.get("response_text", "")).strip()
        emoji = str(data.get("emoji", "🙂")).strip()
        action_prompt = str(data.get("action_prompt", "")).strip()
        steps = data.get("steps") or []
        tags = data.get("tags") or []
        if not isinstance(steps, list):
            steps = []
        if not isinstance(tags, list):
            tags = []
        steps = [str(step).strip() for step in steps][:3]
        tags = [str(tag).strip() for tag in tags][:4]

        return MoodSolution(
            response_text=response_text,
            emoji=emoji,
            action_prompt=action_prompt,
            steps=steps,
            tags=tags,
            source="openai",
            model_used=model_name,
        )
    except Exception:
        if getattr(settings, "OPENAI_REQUIRED", True):
            raise RuntimeError("OPENAI_RESPONSE_ERROR")
        return _generate_local_solution(problem_text, mood)


def update_weekly_insight(user) -> MoodInsight | None:
    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())
    requests = MoodRequest.objects.filter(user=user, created_at__date__gte=week_start)
    if requests.count() < 3:
        return None

    mood_counts: dict[str, int] = {}
    for item in requests:
        mood_counts[item.mood] = mood_counts.get(item.mood, 0) + 1
    top_mood = max(mood_counts, key=mood_counts.get)
    trend = f"Bu hafta eng ko'p mood: {top_mood}."

    summary_map = {
        "happy": "Energiya yuqori. Katta vazifalarni shu momentumda yakunlang.",
        "stressed": "Yuklama baland. Vazifalarni 25 daqiqalik bloklarga bo'ling.",
        "tired": "Dam olish kerak. Mini tanaffuslar va suv rejasi foyda beradi.",
        "motivated": "Motivatsiya kuchli. Eng katta maqsadni 3 qadamga bo'ling.",
    }
    summary = summary_map.get(top_mood, "Trend aniqlanmoqda. Kichik qadam bilan davom eting.")

    insight, _ = MoodInsight.objects.update_or_create(
        user=user,
        week_start=week_start,
        defaults={"summary": summary, "mood_trend": trend},
    )
    return insight
