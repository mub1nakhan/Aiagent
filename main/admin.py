from django.contrib import admin

from .models import Feedback, MoodInsight, MoodRequest, MoodStep, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "display_name", "theme_preference", "created_at")
    search_fields = ("display_name", "user__username")


class MoodStepInline(admin.TabularInline):
    model = MoodStep
    extra = 0


@admin.register(MoodRequest)
class MoodRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "mood", "intensity", "source", "created_at", "short_problem")
    list_filter = ("mood", "source", "created_at")
    search_fields = ("title", "problem_text", "response_text", "action_prompt", "tags")
    ordering = ("-created_at",)
    inlines = [MoodStepInline]

    def short_problem(self, obj: MoodRequest) -> str:
        return (obj.problem_text[:60] + "...") if len(obj.problem_text) > 60 else obj.problem_text

    short_problem.short_description = "Problem"


@admin.register(MoodInsight)
class MoodInsightAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "week_start", "created_at")
    search_fields = ("summary", "mood_trend", "user__username")
    list_filter = ("week_start",)


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("id", "request", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("comment",)
