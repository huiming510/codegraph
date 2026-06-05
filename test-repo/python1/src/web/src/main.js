import "./styles.css";
import { initSidebar } from "./shared.js";
import "./kb.js";
import "./chat.js";

const ROUTES = {
  kb: "kbPage",
  chat: "chatPage",
};

function normalizeRoute(raw) {
  const name = raw.replace(/^#/, "").trim().toLowerCase();
  return name === "chat" ? "chat" : "kb";
}

function applyRoute(route) {
  const kbPage = document.getElementById(ROUTES.kb);
  const chatPage = document.getElementById(ROUTES.chat);
  const links = document.querySelectorAll(".sidebar-nav a[data-route]");
  if (!kbPage || !chatPage) return;

  const isChat = route === "chat";
  kbPage.classList.toggle("active", !isChat);
  chatPage.classList.toggle("active", isChat);

  links.forEach((link) => {
    link.classList.toggle("active", link.dataset.route === route);
  });
}

function syncRoute() {
  applyRoute(normalizeRoute(window.location.hash));
}

initSidebar();
window.addEventListener("hashchange", syncRoute);
syncRoute();
