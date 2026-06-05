const API_BASE_URL = "http://192.168.10.187:8000";

export function initSidebar() {
  const shell = document.querySelector(".app-shell");
  const toggleBtn = document.getElementById("sidebarToggle");
  if (!shell || !toggleBtn) return;

  toggleBtn.addEventListener("click", () => {
    shell.classList.toggle("sidebar-collapsed");
  });
}

export function getBaseUrl() {
  return API_BASE_URL.replace(/\/$/, "");
}

export async function apiFetch(path, options = {}) {
  const resp = await fetch(`${getBaseUrl()}${path}`, {
    ...options,
    headers: {
      ...(options.headers || {}),
    },
  });

  let data;
  const text = await resp.text();
  try {
    data = text ? JSON.parse(text) : { raw: "" };
  } catch {
    data = { raw: text };
  }

  if (!resp.ok) {
    throw new Error(typeof data === "object" ? JSON.stringify(data) : String(data));
  }

  return data;
}

export function setResult(node, data, isError = false) {
  node.style.color = isError ? "#9e1f1f" : "#666";
  node.textContent = typeof data === "string" ? data : JSON.stringify(data, null, 2);
}

export function ensureValue(v, name) {
  if (!v) throw new Error(`${name} 不能为空`);
}

export function parseMaybeJson(v) {
  try {
    return JSON.parse(v);
  } catch {
    return v;
  }
}

export function escapeHtml(text) {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
