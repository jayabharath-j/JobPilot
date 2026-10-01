// ============================================================
// DELETE CONFIRMATION
// ============================================================

function confirmDelete(type) {
  return confirm(`Are you sure you want to delete this ${type}?`);
}

// ============================================================
// APPLY THEME
// ============================================================

function applyTheme(theme) {
  document.documentElement.setAttribute("data-bs-theme", theme);

  localStorage.setItem("jobpilot-theme", theme);

  document.querySelectorAll(".theme-toggle").forEach((button) => {
    const icon = button.querySelector(".theme-icon");

    const label = button.querySelector(".theme-label");

    const isDark = theme === "dark";

    // Theme icon

    if (icon) {
      icon.textContent = isDark ? "☀️" : "🌙";
    }

    // Theme label

    if (label) {
      label.textContent = isDark ? "Light mode" : "Dark mode";
    }

    // Accessibility label

    button.setAttribute(
      "aria-label",
      isDark ? "Switch to light mode" : "Switch to dark mode",
    );
  });
}

// ============================================================
// TOGGLE THEME
// ============================================================

function toggleTheme() {
  const currentTheme =
    document.documentElement.getAttribute("data-bs-theme") || "light";

  applyTheme(currentTheme === "dark" ? "light" : "dark");
}

// ============================================================
// INTERVIEW COUNTDOWNS
// ============================================================

function updateCountdowns() {
  document.querySelectorAll(".interview-card").forEach((card) => {
    const date = card.dataset.date;

    const time = card.dataset.time || "00:00";

    const target = new Date(`${date}T${time}`);

    const countdown = card.querySelector(".countdown");

    if (!countdown) {
      return;
    }

    if (Number.isNaN(target.getTime())) {
      return;
    }

    const difference = target - new Date();

    // Interview already completed

    if (difference < 0) {
      countdown.textContent = "Completed";

      countdown.className = "countdown small text-secondary mt-1";

      return;
    }

    // Convert milliseconds

    const days = Math.floor(difference / 86400000);

    const hours = Math.floor((difference % 86400000) / 3600000);

    const minutes = Math.floor((difference % 3600000) / 60000);

    // Display countdown

    countdown.textContent = days
      ? `⏳ ${days}d ${hours}h remaining`
      : `⏳ ${hours}h ${minutes}m remaining`;

    countdown.className = "countdown small text-primary fw-semibold mt-1";
  });
}

// ============================================================
// PAGE LOAD
// ============================================================

document.addEventListener("DOMContentLoaded", () => {
  // Apply saved/current theme

  applyTheme(document.documentElement.getAttribute("data-bs-theme") || "light");

  // Update interview countdowns

  updateCountdowns();

  // Refresh countdown every minute

  setInterval(updateCountdowns, 60000);
});
