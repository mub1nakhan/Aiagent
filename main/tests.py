import json

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from .models import MoodRequest


class MoodAppTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="tester", password="pass1234")

    def test_home_page_loads(self):
        self.client.login(username="tester", password="pass1234")
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    @override_settings(OPENAI_REQUIRED=False)
    def test_solve_api_valid(self):
        self.client.login(username="tester", password="pass1234")
        payload = {"problem": "Deadline yaqin", "mood": "stressed"}
        response = self.client.post(
            "/api/solve/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertIn("response_text", data)
        self.assertEqual(MoodRequest.objects.count(), 1)
        self.assertEqual(MoodRequest.objects.first().user, self.user)

    @override_settings(OPENAI_REQUIRED=False)
    def test_solve_api_invalid(self):
        self.client.login(username="tester", password="pass1234")
        payload = {"problem": "", "mood": "unknown"}
        response = self.client.post(
            "/api/solve/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["ok"])
