# -*- coding: utf-8 -*-
"""
Backend 侧：解析服务客户端(LinkragServerClient)。
解析服务实现见 file/db/app，单独启动时：uvicorn server.app:app。
"""
from .client import LinkragServerClient

__all__ = ["LinkragServerClient"]
