const btn = document.getElementById("darkToggle");

// Apply saved theme on load
if (localStorage.theme === "dark") {
    document.body.classList.add("dark");
    btn.textContent = "Light Mode";
} else {
    btn.textContent = "Dark Mode";
}

// Toggle theme on click
btn.addEventListener("click", () => {
    const isDark = document.body.classList.toggle("dark");
    localStorage.theme = isDark ? "dark" : "light";
    btn.textContent = isDark ? "Light Mode" : "Dark Mode";
});
// Highlight active nav link
document.querySelectorAll(".nav-link").forEach(link => {
    if (link.href === window.location.href) {
        link.classList.add("active");
    }
});
