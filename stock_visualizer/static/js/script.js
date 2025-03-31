// Theme toggle
document.getElementById("theme-toggle").addEventListener("click", () => {
    document.body.classList.toggle("light-theme");
    localStorage.setItem("theme", document.body.classList.contains("light-theme") ? "light" : "dark");
});

// Load theme on page load
window.addEventListener("load", () => {
    if (localStorage.getItem("theme") === "light") {
        document.body.classList.add("light-theme");
    }
});

// Auto-refresh charts every 60 seconds
setInterval(() => {
    location.reload();
}, 60000);  