import {
  apiFetch,
  ensureValue,
  escapeHtml,
  getBaseUrl,
  parseMaybeJson,
  setResult,
} from "./shared.js";

const state = {
  messages: [],
  currentAssistantId: null,
  processingId: null,
  sessionId: "",
};

const $ = (id) => document.getElementById(id);

const el = {
  modelName: $("modelName"),
  modelBaseUrl: $("modelBaseUrl"),
  apiKey: $("apiKey"),
  thinking: $("thinking"),
  updateModelBtn: $("updateModelBtn"),
  settingsResult: $("settingsResult"),
  chatIndex: $("chatIndex"),
  searchMethod: $("searchMethod"),
  topK: $("topK"),
  threshold: $("threshold"),
  generateModel: $("generateModel"),
  temperature: $("temperature"),
  topP: $("topP"),
  utterance: $("utterance"),
  sendBtn: $("sendBtn"),
  clearBtn: $("clearBtn"),
  messages: $("messages"),
};

function createMessage(role, content = "") {
  const id = `${role}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  state.messages.push({ id, role, content, refs: null });
  renderMessages();
  return id;
}

function showProcessing() {
  if (state.processingId) return;
  const id = `processing-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  state.processingId = id;
  state.currentAssistantId = id;
  state.messages.push({
    id,
    role: "assistant",
    content: "",
    refs: null,
    processing: true,
  });
  renderMessages();
}

function hideProcessing() {
  if (!state.processingId) return;
  state.messages = state.messages.filter((m) => m.id !== state.processingId);
  state.processingId = null;
  renderMessages();
}

function updateMessage(id, updater) {
  const msg = state.messages.find((m) => m.id === id);
  if (!msg) return;
  updater(msg);
  renderMessages();
}

function getLastAssistantMessageId() {
  for (let i = state.messages.length - 1; i >= 0; i -= 1) {
    if (state.messages[i].role === "assistant" && !state.messages[i].processing) {
      return state.messages[i].id;
    }
  }
  return null;
}

function normalizeReferences(refs) {
  if (Array.isArray(refs)) return refs;
  if (!refs || typeof refs !== "object") return [];
  if (Array.isArray(refs.references)) return refs.references;
  if (Array.isArray(refs.refs)) return refs.refs;
  if (Array.isArray(refs.items)) return refs.items;

  // Some backends send an object map: { "1": {...}, "2": {...} }
  const values = Object.values(refs);
  if (values.length && values.every((v) => v && typeof v === "object")) {
    return values;
  }
  return [];
}

function renderReferences(refs) {
  const list = normalizeReferences(refs);
  if (!list.length) return "";

  const items = list
    .map((ref) => {
      const refId = ref?.ref_id;
      return { ...ref, __sortId: Number.isFinite(Number(refId)) ? Number(refId) : Number.MAX_SAFE_INTEGER };
    })
    .sort((a, b) => a.__sortId - b.__sortId)
    .map((ref) => {
      const refId = ref?.ref_id ?? "-";
      const fileName =
        ref?.metadata?.file_name || ref?.metadata?.filename || ref?.metadata?.name || ref?.doc_id || "unknown";
      return `<li class="ref-item"><span class="ref-id">[${escapeHtml(String(refId))}]</span><span class="ref-file">${escapeHtml(String(fileName))}</span></li>`;
    })
    .join("");

  return `<div class="refs"><strong>references:</strong><ul class="ref-list">${items}</ul></div>`;
}

function renderMessages() {
  el.messages.innerHTML = state.messages
    .map((m) => {
      if (m.processing) {
        return `
      <div class="message assistant processing">
        <div class="meta">assistant</div>
        <div class="content"><span class="spinner"></span></div>
      </div>
    `;
      }
      const refs = m.refs ? renderReferences(m.refs) : "";
      return `
      <div class="message ${m.role}">
        <div class="meta">${m.role === "user" ? "user" : "assistant"}</div>
        <div class="content">${escapeHtml(m.content)}</div>
        ${refs}
      </div>
    `;
    })
    .join("");

  el.messages.scrollTop = el.messages.scrollHeight;
}

async function streamChat(body) {
  const resp = await fetch(`${getBaseUrl()}/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify(body),
  });

  if (!resp.ok || !resp.body) {
    const errText = await resp.text();
    throw new Error(errText || `HTTP ${resp.status}`);
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() || "";

    for (const chunk of chunks) {
      const lines = chunk.split("\n");
      let event = "message";
      let data = "";

      for (const line of lines) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        if (line.startsWith("data:")) data += `${line.slice(5).trim()}\n`;
      }

      data = data.trim();
      handleSseEvent(event, data);
    }
  }
}

function handleSseEvent(event, data) {
  switch (event) {
    case "session_id":
      state.sessionId = data;
      break;
    case "start":
      if (!state.currentAssistantId) {
        state.currentAssistantId = createMessage("assistant", "");
      }
      break;
    case "delta":
      if (!state.currentAssistantId) state.currentAssistantId = createMessage("assistant", "");
      updateMessage(state.currentAssistantId, (m) => {
        if (m.processing) {
          m.processing = false;
          state.processingId = null;
        }
        m.content += data;
      });
      break;
    case "references":
      {
        const targetId = state.currentAssistantId || getLastAssistantMessageId();
        if (!targetId) return;
        updateMessage(targetId, (m) => {
          const parsed = parseMaybeJson(data);
          // Merge with previous refs if event is streamed multiple times.
          const merged = [...normalizeReferences(m.refs), ...normalizeReferences(parsed)];
          m.refs = merged.length ? merged : parsed;
        });
      }
      break;
    case "error":
      if (!state.currentAssistantId) state.currentAssistantId = createMessage("assistant", "");
      updateMessage(state.currentAssistantId, (m) => {
        if (m.processing) {
          m.processing = false;
          state.processingId = null;
        }
        m.content += `\n[ERROR] ${data}`;
      });
      break;
    case "end":
      hideProcessing();
      state.currentAssistantId = null;
      break;
    case "done":
      hideProcessing();
      break;
    default:
      break;
  }
}

el.updateModelBtn.addEventListener("click", async () => {
  try {
    const model = el.modelName.value.trim();
    const base_url = el.modelBaseUrl.value.trim();
    const api_key = el.apiKey.value.trim();
    ensureValue(model, "model");
    ensureValue(base_url, "base_url");
    ensureValue(api_key, "api_key");

    const data = await apiFetch("/api/update_model", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model,
        base_url,
        api_key,
        thinking: !!el.thinking.checked,
      }),
    });

    setResult(el.settingsResult, data);
  } catch (e) {
    setResult(el.settingsResult, e.message, true);
  }
});

async function sendChat() {
  const utterance = el.utterance.value.trim();
  const index = el.chatIndex.value.trim();

  if (!utterance) return;

  try {
    ensureValue(index, "chat index");

    createMessage("user", utterance);
    state.currentAssistantId = null;
    showProcessing();
    el.utterance.value = "";
    el.sendBtn.disabled = true;

    const body = {
      session_id: state.sessionId || `s-${Date.now()}`,
      utterance,
      index,
      search_options: {
        search_method: el.searchMethod.value,
      },
      generate_options: {},
    };

    if (el.topK.value) body.search_options.top_k = Number(el.topK.value);
    if (el.threshold.value) body.search_options.threshold = Number(el.threshold.value);
    if (el.generateModel.value.trim()) body.generate_options.model = el.generateModel.value.trim();
    if (el.temperature.value) body.generate_options.temperature = Number(el.temperature.value);
    if (el.topP.value) body.generate_options.top_p = Number(el.topP.value);

    await streamChat(body);
  } catch (e) {
    hideProcessing();
    createMessage("assistant", `[请求失败] ${e.message}`);
  } finally {
    hideProcessing();
    el.sendBtn.disabled = false;
  }
}

el.sendBtn.addEventListener("click", sendChat);
el.clearBtn.addEventListener("click", () => {
  state.messages = [];
  state.currentAssistantId = null;
  state.processingId = null;
  state.sessionId = "";
  renderMessages();
});

el.utterance.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") sendChat();
});
