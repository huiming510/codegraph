import { apiFetch, ensureValue, setResult } from "./shared.js";

const $ = (id) => document.getElementById(id);

const el = {
  indexName: $("indexName"),
  createIndexBtn: $("createIndexBtn"),
  deleteIndexBtn: $("deleteIndexBtn"),
  infoIndexBtn: $("infoIndexBtn"),
  indexResult: $("indexResult"),
  chunkSize: $("chunkSize"),
  chunkOverlap: $("chunkOverlap"),
  chunkStrategy: $("chunkStrategy"),
  updatePipelineBtn: $("updatePipelineBtn"),
  pipelineResult: $("pipelineResult"),
  uploadIndex: $("uploadIndex"),
  uploadFile: $("uploadFile"),
  uploadBtn: $("uploadBtn"),
  uploadResult: $("uploadResult"),
};

el.createIndexBtn.addEventListener("click", async () => {
  try {
    const index = el.indexName.value.trim();
    ensureValue(index, "index");
    const data = await apiFetch("/index/create", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ index }),
    });
    setResult(el.indexResult, data);
  } catch (e) {
    setResult(el.indexResult, e.message, true);
  }
});

el.deleteIndexBtn.addEventListener("click", async () => {
  try {
    const index = el.indexName.value.trim();
    ensureValue(index, "index");
    const data = await apiFetch(`/index/delete?index=${encodeURIComponent(index)}`, {
      method: "DELETE",
    });
    setResult(el.indexResult, data);
  } catch (e) {
    setResult(el.indexResult, e.message, true);
  }
});

el.infoIndexBtn.addEventListener("click", async () => {
  try {
    const index = el.indexName.value.trim();
    ensureValue(index, "index");
    const data = await apiFetch("/index/info", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ index }),
    });
    setResult(el.indexResult, data);
  } catch (e) {
    setResult(el.indexResult, e.message, true);
  }
});

el.updatePipelineBtn.addEventListener("click", async () => {
  try {
    const body = {};
    if (el.chunkSize.value) body.chunk_size = Number(el.chunkSize.value);
    if (el.chunkOverlap.value) body.chunk_overlap = Number(el.chunkOverlap.value);
    if (el.chunkStrategy.value.trim()) body.chunk_strategy = el.chunkStrategy.value.trim();

    const data = await apiFetch("/api/update_text_pipeline", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    setResult(el.pipelineResult, data);
  } catch (e) {
    setResult(el.pipelineResult, e.message, true);
  }
});

el.uploadBtn.addEventListener("click", async () => {
  try {
    const index = el.uploadIndex.value.trim();
    ensureValue(index, "index");

    if (!el.uploadFile.files || !el.uploadFile.files[0]) {
      throw new Error("请选择文件");
    }

    const docId = `doc-${Date.now()}`;
    const fd = new FormData();
    fd.append("payload", JSON.stringify({ doc_id: docId, index }));
    fd.append("doc_id", docId);
    fd.append("index", index);
    fd.append("file", el.uploadFile.files[0]);

    const data = await apiFetch("/file/upload_stream", {
      method: "POST",
      body: fd,
    });

    setResult(el.uploadResult, data);
  } catch (e) {
    setResult(el.uploadResult, e.message, true);
  }
});
