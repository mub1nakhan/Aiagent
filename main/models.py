from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    THEME_LIGHT = "light"
    THEME_DARK = "dark"
    THEME_CHOICES = [
        (THEME_LIGHT, "Light"),
        (THEME_DARK, "Dark"),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    display_name = models.CharField(max_length=80, blank=True)
    theme_preference = models.CharField(max_length=10, choices=THEME_CHOICES, default=THEME_LIGHT)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.display_name or self.user.username


class MoodRequest(models.Model):
    MOOD_HAPPY = "happy"
    MOOD_STRESSED = "stressed"
    MOOD_TIRED = "tired"
    MOOD_MOTIVATED = "motivated"

    MOOD_CHOICES = [
        (MOOD_HAPPY, "Happy"),
        (MOOD_STRESSED, "Stressed"),
        (MOOD_TIRED, "Tired"),
        (MOOD_MOTIVATED, "Motivated"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mood_requests",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=120, blank=True)
    problem_text = models.TextField()
    mood = models.CharField(max_length=20, choices=MOOD_CHOICES)
    intensity = models.PositiveSmallIntegerField(default=3)
    tags = models.CharField(max_length=200, blank=True)
    response_text = models.TextField()
    emoji = models.CharField(max_length=10)
    action_prompt = models.CharField(max_length=255)
    model_used = models.CharField(max_length=60, blank=True)
    source = models.CharField(max_length=20, default="local")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.get_mood_display()} - {self.created_at:%Y-%m-%d %H:%M}"

    @property
    def tag_list(self) -> list[str]:
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(",") if tag.strip()]


class MoodStep(models.Model):
    request = models.ForeignKey(MoodRequest, on_delete=models.CASCADE, related_name="steps")
    order = models.PositiveSmallIntegerField(default=1)
    text = models.CharField(max_length=200)
    done = models.BooleanField(default=False)

    class Meta:
        ordering = ["order"]

    def __str__(self) -> str:
        return f"{self.order}. {self.text}"


class MoodInsight(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="insights")
    summary = models.TextField()
    mood_trend = models.CharField(max_length=120, blank=True)
    week_start = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Insight {self.week_start}"


class Feedback(models.Model):
    request = models.ForeignKey(MoodRequest, on_delete=models.CASCADE, related_name="feedbacks")
    rating = models.PositiveSmallIntegerField(default=5)
    comment = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.rating}/5 for {self.request_id}"
