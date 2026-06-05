"""LLM：默认模型配置、供应商树、按模型配置、可选模型、测试连接"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Any

from config import get_llm_config
from llm import LLMFactory, get_llm, LLMConfig
from llm.base import LLMProvider
from logger import logger
from .common import success_response

router = APIRouter(prefix="/api/llm", tags=["LLM"])

# 由 main 注入的 llm 实例
_llm = None
# 按 provider|model 存储的配置，供前端弹窗加载/保存
_model_configs: dict[str, dict] = {}

# 默认模型配置：llm / embedding / vlm / asr / rerank / tts，值为 "provider|model" 或 ""
_default_models: dict[str, str] = {
    "llm": "",
    "embedding": "",
    "vlm": "",
    "asr": "",
    "rerank": "",
    "tts": "",
}

# 可选模型供应商（右侧「可选模型」面板）：id、名称、图标、能力标签
_OPTIONAL_PROVIDERS = [
    {"id": "gitee_ai", "name": "GiteeAI", "icon": "gitee", "capabilities": ["LLM", "TEXT EMBEDDING", "TEXT RE-RANK", "SPEECH2TEXT", "IMAGE2TEXT"]},
    {"id": "fish_audio", "name": "Fish Audio", "icon": "fish", "capabilities": ["TTS"]},
    {"id": "deer_api", "name": "DeerAPI", "icon": "deer", "capabilities": ["LLM", "TEXT EMBEDDING", "IMAGE2TEXT"]},
    {"id": "deep_infra", "name": "DeepInfra", "icon": "deep", "capabilities": ["LLM", "TEXT EMBEDDING", "TTS", "SPEECH2TEXT", "MODERATION"]},
    {"id": "comet_api", "name": "CometAPI", "icon": "comet", "capabilities": ["LLM", "TEXT EMBEDDING", "IMAGE2TEXT"]},
    {"id": "openai", "name": "OpenAI", "icon": "openai", "capabilities": ["LLM", "TEXT EMBEDDING", "TTS", "SPEECH2TEXT", "IMAGE2TEXT"]},
    {"id": "anthropic", "name": "Anthropic", "icon": "anthropic", "capabilities": ["LLM", "MODERATION"]},
    {"id": "ollama", "name": "Ollama", "icon": "ollama", "capabilities": ["LLM", "TEXT EMBEDDING", "IMAGE2TEXT"]},
    {"id": "zhipu", "name": "智谱 AI", "icon": "zhipu", "capabilities": ["LLM", "TEXT EMBEDDING"]},
    {"id": "qwen", "name": "通义千问", "icon": "qwen", "capabilities": ["LLM", "TEXT EMBEDDING", "SPEECH2TEXT"]},
]

# 供应商与模型静态数据（与前端一致）
_PROVIDER_LABELS = {
    "openai": "OpenAI",
    "azure_openai": "Azure OpenAI",
    "anthropic": "Anthropic Claude",
    "ollama": "Ollama (本地)",
    "zhipu": "智谱 AI",
    "qwen": "通义千问",
    "mock": "Mock (测试)",
    "gitee_ai": "GiteeAI",
    "fish_audio": "Fish Audio",
    "deer_api": "DeerAPI",
    "deep_infra": "DeepInfra",
    "comet_api": "CometAPI",
}
# 供应商图标（公有/私有树节点展示）
_PROVIDER_ICONS = {
    "openai": "🤖",
    "azure_openai": "☁️",
    "anthropic": "🧠",
    "ollama": "🦙",
    "zhipu": "🇨🇳",
    "qwen": "🌐",
    "mock": "🧪",
    "gitee_ai": "🔗",
    "fish_audio": "🐟",
    "deer_api": "🦌",
    "deep_infra": "◉",
    "comet_api": "☄",
}
_MODELS_BY_PROVIDER = {
    "openai": [{"value": "gpt-4o", "label": "GPT-4o"}, {"value": "gpt-4o-mini", "label": "GPT-4o Mini"}, {"value": "gpt-4-turbo", "label": "GPT-4 Turbo"}, {"value": "gpt-3.5-turbo", "label": "GPT-3.5 Turbo"}],
    "azure_openai": [{"value": "gpt-4o", "label": "GPT-4o"}, {"value": "gpt-4", "label": "GPT-4"}, {"value": "gpt-35-turbo", "label": "GPT-3.5 Turbo"}],
    "anthropic": [{"value": "claude-3-5-sonnet-20241022", "label": "Claude 3.5 Sonnet"}, {"value": "claude-3-opus-20240229", "label": "Claude 3 Opus"}, {"value": "claude-3-haiku-20240307", "label": "Claude 3 Haiku"}],
    "ollama": [{"value": "llama3.2", "label": "Llama 3.2"}, {"value": "qwen2.5", "label": "Qwen 2.5"}, {"value": "mistral", "label": "Mistral"}, {"value": "deepseek-r1", "label": "DeepSeek R1"}],
    "zhipu": [{"value": "glm-4-plus", "label": "GLM-4 Plus"}, {"value": "glm-4", "label": "GLM-4"}, {"value": "glm-4-flash", "label": "GLM-4 Flash"}],
    "qwen": [{"value": "qwen-max", "label": "Qwen Max"}, {"value": "qwen-plus", "label": "Qwen Plus"}, {"value": "qwen-turbo", "label": "Qwen Turbo"}],
    "mock": [{"value": "mock", "label": "Mock Model"}],
}
# 共有模型(API)：需 API Key 的供应商
_SHARED_PROVIDERS = ["openai", "azure_openai", "anthropic", "zhipu", "qwen"]
# 私有模型：本地/模拟
_PRIVATE_PROVIDERS = ["ollama", "mock"]


def set_llm(llm):
    global _llm
    _llm = llm


def get_llm_instance():
    if _llm is None:
        raise RuntimeError("LLM not initialized")
    return _llm


def _tree_children(provider_keys: List[str]) -> List[dict]:
    children = []
    for p in provider_keys:
        if p not in _PROVIDER_LABELS or p not in _MODELS_BY_PROVIDER:
            continue
        models = _MODELS_BY_PROVIDER[p]
        model_nodes = [
            {"key": f"{p}|{m['value']}", "title": m["label"], "type": "model", "provider": p, "model": m["value"], "isLeaf": True}
            for m in models
        ]
        children.append({
            "key": p,
            "title": _PROVIDER_LABELS[p],
            "type": "provider",
            "provider": p,
            "icon": _PROVIDER_ICONS.get(p, ""),
            "children": model_nodes,
        })
    return children


def _flat_models(provider_keys: List[str]) -> List[dict]:
    out = []
    for p in provider_keys:
        if p not in _PROVIDER_LABELS or p not in _MODELS_BY_PROVIDER:
            continue
        is_public = p in _SHARED_PROVIDERS
        scope_tag = "公有" if is_public else "私有"
        model_type = "API 模型" if is_public else "本地/模拟"
        for m in _MODELS_BY_PROVIDER[p]:
            out.append({
                "provider": p,
                "model": m["value"],
                "modelLabel": m["label"],
                "providerLabel": _PROVIDER_LABELS[p],
                "icon": _PROVIDER_ICONS.get(p, ""),
                "modelType": model_type,
                "useModel": m["value"],
                "creator": _PROVIDER_LABELS[p],
                "scopeTag": scope_tag,
            })
    return out


class DefaultModelsUpdate(BaseModel):
    llm: Optional[str] = None
    embedding: Optional[str] = None
    vlm: Optional[str] = None
    asr: Optional[str] = None
    rerank: Optional[str] = None
    tts: Optional[str] = None


def _default_model_options_for_type(provider_keys: List[str]) -> List[dict]:
    options = []
    for p in provider_keys:
        if p not in _MODELS_BY_PROVIDER:
            continue
        label = _PROVIDER_LABELS.get(p, p)
        for m in _MODELS_BY_PROVIDER[p]:
            options.append({"value": f"{p}|{m['value']}", "label": f"{label} - {m['label']}"})
    return options


@router.get("/default-models")
def get_default_models():
    """获取各类型默认模型配置（llm / embedding / vlm / asr / rerank / tts）"""
    return success_response(data=dict(_default_models))


@router.get("/default-model-options")
def get_default_model_options():
    """获取设置默认模型表单中各类型的下拉选项"""
    all_providers = list(_PROVIDER_LABELS.keys())
    llm_providers = [p for p in all_providers if p in _MODELS_BY_PROVIDER]
    return success_response(data={
        "llm": _default_model_options_for_type(llm_providers),
        "embedding": _default_model_options_for_type(llm_providers),
        "vlm": _default_model_options_for_type(llm_providers),
        "asr": _default_model_options_for_type(llm_providers),
        "rerank": _default_model_options_for_type(llm_providers),
        "tts": _default_model_options_for_type(llm_providers),
    })


@router.post("/default-models")
def update_default_models(body: DefaultModelsUpdate):
    """更新默认模型配置"""
    global _default_models
    if body.llm is not None:
        _default_models["llm"] = body.llm or ""
    if body.embedding is not None:
        _default_models["embedding"] = body.embedding or ""
    if body.vlm is not None:
        _default_models["vlm"] = body.vlm or ""
    if body.asr is not None:
        _default_models["asr"] = body.asr or ""
    if body.rerank is not None:
        _default_models["rerank"] = body.rerank or ""
    if body.tts is not None:
        _default_models["tts"] = body.tts or ""
    return success_response(data=dict(_default_models))


def _get_model_label(provider: str, model: str) -> str:
    if provider in _MODELS_BY_PROVIDER:
        for m in _MODELS_BY_PROVIDER[provider]:
            if m["value"] == model:
                return m["label"]
    return model


@router.get("/added-providers")
def get_added_providers():
    """获取已添加的模型（按供应商分组），用于左侧「添加了的模型」"""
    out = []
    seen = set()
    for key in _model_configs:
        if "|" not in key:
            continue
        provider, model = key.split("|", 1)
        if provider in seen:
            continue
        seen.add(provider)
        models = [
            {"model": m["model"], "modelLabel": _get_model_label(provider, m["model"])}
            for k, m in _model_configs.items()
            if k.startswith(provider + "|")
        ]
        out.append({
            "provider": provider,
            "providerLabel": _PROVIDER_LABELS.get(provider, provider),
            "icon": _PROVIDER_ICONS.get(provider, "🤖"),
            "models": models,
        })
    return success_response(data=out)


def _flat_optional_models(provider_list: List[dict]) -> List[dict]:
    """将可选供应商展开为扁平的可选模型列表（一行一个模型）"""
    out = []
    for p in provider_list:
        pid = p.get("id", "")
        if pid not in _MODELS_BY_PROVIDER:
            continue
        provider_label = _PROVIDER_LABELS.get(pid, p.get("name", pid))
        icon = _PROVIDER_ICONS.get(pid, "🤖")
        caps = p.get("capabilities") or []
        for m in _MODELS_BY_PROVIDER[pid]:
            out.append({
                "provider": pid,
                "providerLabel": provider_label,
                "model": m["value"],
                "modelLabel": m["label"],
                "icon": icon,
                "capabilities": caps,
            })
    return out


@router.get("/optional-providers")
def get_optional_providers(
    search: Optional[str] = Query(None),
    capability: Optional[str] = Query(None),
):
    """获取可选模型供应商列表（右侧面板），支持搜索和按能力筛选"""
    items = list(_OPTIONAL_PROVIDERS)
    if search:
        q = search.strip().lower()
        items = [p for p in items if q in p["name"].lower()]
    if capability and capability.upper() not in ("", "ALL"):
        cap_val = capability.strip()
        items = [p for p in items if cap_val in p["capabilities"]]
    return success_response(data=items)


def _normalize_capability(capability) -> Optional[str]:
    """规范化 capability 参数：支持 str 或多值时的 list，去空格，ALL 视为空"""
    if capability is None:
        return None
    if isinstance(capability, (list, tuple)):
        capability = capability[0] if capability else None
    if capability is None:
        return None
    s = str(capability).strip()
    if not s or s.upper() == "ALL":
        return None
    return s


@router.get("/optional-models")
def get_optional_models(
    search: Optional[str] = Query(None),
    capability: Optional[str] = Query(None),
):
    """获取可选模型扁平列表（一行一个模型），支持搜索和按能力筛选。
    查询参数：?search=xxx&capability=MODERATION（平铺，不要用 params[capability]）。"""
    items = list(_OPTIONAL_PROVIDERS)
    if search:
        q = search.strip().lower()
        items = [p for p in items if q in p["name"].lower()]
    cap_val = _normalize_capability(capability)
    if cap_val:
        # 按能力筛选供应商（大小写不敏感）
        cap_upper = cap_val.upper()
        items = [
            p for p in items
            if any(cap_upper == (c or "").upper() for c in (p.get("capabilities") or []))
        ]
    flat = _flat_optional_models(items)
    if search:
        q = search.strip().lower()
        flat = [
            x for x in flat
            if q in (x.get("providerLabel") or "").lower() or q in (x.get("modelLabel") or "").lower()
        ]
    if cap_val:
        # 对扁平列表再次按能力过滤，确保只返回包含该能力的模型
        cap_upper = cap_val.upper()
        flat = [
            x for x in flat
            if any(cap_upper == (c or "").upper() for c in (x.get("capabilities") or []))
        ]
    return success_response(data=flat)


@router.get("/tree")
def get_llm_tree():
    """获取大模型供应商树：全部模型(无子节点，点击取列表)、公有模型(API)/私有模型(可展开，带图标)"""
    tree = [
        {"key": "all", "title": "全部模型", "type": "root", "icon": "📋", "children": [], "selectable": True},
        {"key": "shared", "title": "公有模型（API）", "type": "root", "icon": "🌐", "children": _tree_children(_SHARED_PROVIDERS)},
        {"key": "private", "title": "私有模型", "type": "root", "icon": "🔒", "children": _tree_children(_PRIVATE_PROVIDERS)},
    ]
    return success_response(data=tree)


@router.get("/models")
def get_models_list(scope: Optional[str] = None, provider: Optional[str] = None):
    """获取模型扁平列表。scope=all 或不传为全部，shared=公有，private=私有；provider 指定时只返回该供应商下的模型"""
    if provider:
        keys = [provider] if provider in _PROVIDER_LABELS else []
    elif scope == "shared":
        keys = _SHARED_PROVIDERS
    elif scope == "private":
        keys = _PRIVATE_PROVIDERS
    else:
        keys = list(_PROVIDER_LABELS.keys())
    return success_response(data=_flat_models(keys))


def _config_key(provider: str, model: str) -> str:
    return f"{provider}|{model}"


class LLMConfigRequest(BaseModel):
    provider: str
    model: Optional[str] = None
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2048
    set_as_current: Optional[bool] = False


@router.get("/providers")
def get_providers():
    """获取支持的 LLM 提供商列表"""
    llm = get_llm_instance()
    return success_response(
        data={
            "providers": LLMFactory.list_providers(),
            "current": llm.get_provider_name(),
        }
    )


@router.get("/config")
def get_model_config(provider: str, model: str):
    """获取指定 provider+model 的配置（用于弹窗回显）"""
    key = _config_key(provider, model)
    if key in _model_configs:
        return success_response(data=_model_configs[key])
    default = {
        "provider": provider,
        "model": model,
        "api_key": "",
        "api_base": "",
        "temperature": 0.7,
        "max_tokens": 2048,
    }
    return success_response(data=default)


@router.delete("/config")
def delete_model_config(provider: str, model: str):
    """删除指定模型的已保存配置"""
    global _model_configs
    key = _config_key(provider, model)
    if key in _model_configs:
        del _model_configs[key]
        logger.info(f"已删除模型配置: {provider} / {model}")
    return success_response(data={"success": True})


@router.post("/config")
async def update_llm_config(request: LLMConfigRequest):
    """保存某模型的 LLM 配置，可选设为当前使用"""
    global _llm, _model_configs
    try:
        provider = request.provider.lower()
        model = request.model or "gpt-3.5-turbo"
        key = _config_key(provider, model)
        cfg = {
            "provider": provider,
            "model": model,
            "api_key": request.api_key or "",
            "api_base": request.api_base or "",
            "temperature": request.temperature if request.temperature is not None else 0.7,
            "max_tokens": request.max_tokens if request.max_tokens is not None else 2048,
        }
        _model_configs[key] = cfg
        if request.set_as_current:
            prov = LLMProvider(provider)
            config = LLMConfig(
                provider=prov,
                model=model,
                api_key=cfg.get("api_key") or None,
                api_base=cfg.get("api_base") or None,
                temperature=cfg["temperature"],
                max_tokens=cfg["max_tokens"],
            )
            _llm = get_llm(config)
            logger.info(f"LLM 当前配置已切换: {provider} / {model}")
        return success_response(data={"success": True, "provider": provider, "model": model})
    except Exception as e:
        logger.error(f"更新 LLM 配置失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


class LLMTestRequest(BaseModel):
    provider: str
    model: Optional[str] = None
    api_key: Optional[str] = None
    api_base: Optional[str] = None


@router.post("/test")
async def test_llm_connection(body: Optional[LLMTestRequest] = None):
    """测试 LLM 连接。不传 body 或 body 无 provider 时用当前实例；传 body 时用指定配置测试"""
    if body is None or not (getattr(body, "provider", None)):
        llm = get_llm_instance()
        try:
            response = await llm.simple_chat("你好，请回复'连接成功'")
            return success_response(data={"success": True, "message": response[:100]})
        except Exception as e:
            logger.error(f"LLM 连接测试失败: {e}")
            return success_response(data={"success": False, "message": str(e)}, msg=str(e))
    try:
        prov = LLMProvider(body.provider.lower())
        config = LLMConfig(
            provider=prov,
            model=body.model or "gpt-3.5-turbo",
            api_key=body.api_key,
            api_base=body.api_base,
        )
        test_llm = get_llm(config)
        response = await test_llm.simple_chat("你好，请回复'连接成功'")
        return success_response(data={"success": True, "message": response[:100]})
    except Exception as e:
        logger.error(f"LLM 连接测试失败: {e}")
        return success_response(data={"success": False, "message": str(e)}, msg=str(e))
