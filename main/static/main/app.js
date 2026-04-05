const form = document.getElementById("mood-form");
const resultBox = document.getElementById("result");
const resultText = document.getElementById("result-text");
const resultEmoji = document.getElementById("result-emoji");
const resultAction = document.getElementById("result-action");
const resultSteps = document.getElementById("result-steps");
const resultTags = document.getElementById("result-tags");

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    return parts.pop().split(";").shift();
  }
  return "";
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const problem = document.getElementById("problem").value.trim();
  const mood = form.querySelector("input[name='mood']:checked")?.value;
  const title = document.getElementById("title")?.value.trim() || "";
  const tags = document.getElementById("tags")?.value.trim() || "";
  const intensity = document.getElementById("intensity")?.value || "3";

  if (!problem || !mood) {
    alert("Muammo va moodni kiriting.");
    return;
  }

  resultBox.hidden = true;
  resultText.textContent = "Yuklanmoqda...";
  resultEmoji.textContent = "⌛";
  resultAction.textContent = "";
  resultSteps.innerHTML = "";
  resultTags.innerHTML = "";

  try {
    const response = await fetch("/api/solve/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      body: JSON.stringify({ problem, mood, title, tags, intensity }),
    });

    const data = await response.json();
    if (!data.ok) {
      alert("Xatolik: " + JSON.stringify(data.errors));
      return;
    }

    resultText.textContent = data.response_text;
    resultEmoji.textContent = data.emoji;
    resultAction.textContent = data.action_prompt;
    if (Array.isArray(data.steps)) {
      data.steps.forEach((step) => {
        const li = document.createElement("li");
        li.textContent = step;
        resultSteps.appendChild(li);
      });
    }
    if (Array.isArray(data.tags)) {
      data.tags.forEach((tag) => {
        const span = document.createElement("span");
        span.className = "tag";
        span.textContent = tag;
        resultTags.appendChild(span);
      });
    }
    resultBox.hidden = false;
  } catch (error) {
    alert("Server bilan aloqa yo'q. Qayta urinib ko'ring.");
  }
});
