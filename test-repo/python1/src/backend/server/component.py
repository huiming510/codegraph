# -*- coding: utf-8 -*-
"""
解析服务核心组件初始化：pipeline、ES、Embedding、任务队列。
从 src 根目录加载 config.yml 并引用 preprocess/index/llm。
"""
import os
import asyncio
import sys
from pathlib import Path

# 将 src 加入路径以便引用 linkrag 各模块（preprocess, index, utils, llm）
_src_root = Path(__file__).resolve().parent.parent.parent
if _src_root and str(_src_root) not in sys.path:
    sys.path.insert(0, str(_src_root))

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from utils import get_logger, load_config
from preprocess import text_pipeline
from index import (
    VllmEmbedding,
    VllmReranker,
    AsyncRetriever,
    AsyncElasticsearchClient,
)
# 从 src/llm 显式加载 OpenAIModel，避免与 backend/llm 的 sys.modules 冲突
import importlib.util
_src_openai_model = _src_root / "llm" / "openai_model.py"
_spec = importlib.util.spec_from_file_location("_src_openai_model", _src_openai_model)
_openai_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_openai_mod)
OpenAIModel = _openai_mod.OpenAIModel

_config_path = _src_root / "config.yml"
if not _config_path.exists():
    raise FileNotFoundError(f"解析服务需要配置文件: {_config_path}")

config = load_config(str(_config_path))
# 解析完成后回调 linkrag-backend 更新文档状态（与 src/server/component 一致）
backend_callback_url = config.get("backend_callback_url") or os.environ.get("BACKEND_CALLBACK_URL") or ""


def _resolve_llm_conf(cfg: dict) -> dict:
    llm_conf = cfg.get("llm")
    if isinstance(llm_conf, list) and llm_conf:
        return llm_conf[0]
    if isinstance(llm_conf, dict):
        return llm_conf
    raise ValueError("config.yml 中 llm 配置无效，需为非空对象或数组")

cache_dir = Path(os.environ.get("HOME", ".")) / ".linkrag"
cache_dir.mkdir(parents=True, exist_ok=True)
(cache_dir / "logs").mkdir(parents=True, exist_ok=True)
upload_dir = cache_dir / "uploads"  # 上传文件保存目录（upload-file 接口使用）
upload_dir.mkdir(parents=True, exist_ok=True)

# LLM（RAG 用，解析服务仅用 pipeline + embed + es）
_llm_conf = _resolve_llm_conf(config)
llm = OpenAIModel(
    model=_llm_conf["model"],
    base_url=_llm_conf["base_url"],
    api_key=_llm_conf.get("api_key", ""),
    thinking=_llm_conf.get("thinking", False),
)

# Elasticsearch
es_client = AsyncElasticsearchClient(url=config["elasticsearch"]["url"])

# Embedding
embed_client = VllmEmbedding(
    url=config["embedding"]["base_url"],
    model=config["embedding"]["model"],
    support_matryoshka=config["embedding"].get("support_matryoshka", False),
    dimensions=config["embedding"].get("dimensions", 1024),
)

# Reranker（解析不用，RAG 用）
if config.get("reranker"):
    reranker = VllmReranker(
        url=config["reranker"]["base_url"],
        model=config["reranker"]["model"],
        llm_arch=config["reranker"].get("llm_arch", True),
    )
else:
    reranker = None

retriever = AsyncRetriever(embedding_client=embed_client, es_client=es_client)

# 文档解析任务队列
task_queue: asyncio.Queue = asyncio.Queue(maxsize=50000)

# 解析完成后由 backend main 注入的「就地回调」，用于同进程时直接更新文档状态，避免 HTTP 回调
parse_status_callback = None

file_logger = get_logger(name="file_logger", log_file=str(cache_dir / "logs" / "file.log"))
app_logger = get_logger(
    name="app_logger",
    add_es=bool(config.get("elasticsearch", {}).get("url")),
    es_hosts=config.get("elasticsearch", {}).get("url"),
)

# 文档解析与分块流水线
pipeline = text_pipeline.Pipeline(
    chunk_size=config.get("pipeline", {}).get("chunk_size", 4096),
    chunk_overlap=config.get("pipeline", {}).get("chunk_overlap", 256),
    logger=file_logger,
    cache_dir=str(cache_dir / "files"),
)
