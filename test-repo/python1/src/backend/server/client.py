# -*- coding: utf-8 -*-
"""
LinkRAG 解析服务客户端：按服务器文件路径提交解析任务，由 linkrag server 完成解析、分块、向量化并写入 ES。
与 src/server/file.py 的 POST /file/upload 接口约定一致：JSON body 为 { "id", "filepath", "index" }。
"""
import httpx
from typing import Optional

from logger import logger


# 解析服务接受的成功状态码（202 为异步接受，200 兼容部分代理）
SUCCESS_STATUS_CODES = (200, 202)


class LinkragServerClient:
    """调用 src/server 提供的文档解析与入库服务（/file/upload）。"""

    def __init__(self, base_url: str, es_index: str = "poc", timeout: float = 60.0):
        """
        Args:
            base_url: 解析服务根地址，如 http://192.168.10.187:8000，不要带末尾斜杠
            es_index: 写入 Elasticsearch 的索引名，需与 linkrag config.yml 中一致
            timeout: 请求超时秒数（解析服务可能需较长时间响应）
        """
        self.base_url = base_url.rstrip("/")
        self.es_index = es_index
        self.timeout = timeout
        self._upload_path = "/file/upload"
        self._upload_file_path = "/file/upload-file"
        self._upload_stream_path = "/file/upload_stream"
        self._index_create_path = "/index/create"
        self._index_delete_path = "/index/delete"
        self._index_info_path = "/index/info"
        self._index_delete_doc_path = "/index/delete-doc"
        self._update_text_pipeline_path = "/api/update_text_pipeline"

    @staticmethod
    def kb_index_name(knowledge_base_id: int) -> str:
        """知识库对应的 ES 索引名默认值（以 linkrag_kb 为前缀）"""
        return f"linkrag_kb_{knowledge_base_id}"

    @staticmethod
    def resolve_kb_index_name(kb) -> str:
        """根据知识库对象解析 ES 索引名：优先使用 kb.es_id，否则 linkrag_kb_{kb.id}"""
        es_id = (getattr(kb, "es_id", None) or "").strip()
        if es_id:
            return es_id
        return f"linkrag_kb_{kb.id}"

    def _build_payload(
        self,
        filepath: str,
        doc_id: str,
        index: Optional[str] = None,
        embedding_base_url: Optional[str] = None,
        embedding_model: Optional[str] = None,
    ) -> dict:
        payload = {
            "id": doc_id,
            "doc_id": doc_id,
            "filepath": filepath,
            "index": index or self.es_index,
        }
        if embedding_base_url:
            payload["embedding_base_url"] = embedding_base_url
        if embedding_model:
            payload["embedding_model"] = embedding_model
        return payload

    def upload_for_parse(
        self,
        filepath: str,
        doc_id: str,
        index: Optional[str] = None,
    ) -> bool:
        """
        提交「按服务器路径解析并入库」任务（同步封装）。
        解析服务会异步处理：解析文档 → 分块 → 向量化 → 写入 ES。
        """
        url = f"{self.base_url}{self._upload_path}"
        payload = self._build_payload(filepath, doc_id, index)
        logger.info(f"调用解析服务: POST {url}  payload={payload}")
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, json=payload)
            if resp.status_code in SUCCESS_STATUS_CODES:
                logger.info(
                    f"解析任务已提交: filepath={filepath}, doc_id={doc_id}, index={payload['index']}, status={resp.status_code}"
                )
                return True
            logger.warning(
                f"解析服务返回异常: status={resp.status_code}, body={resp.text!r}"
            )
            return False
        except httpx.TimeoutException as e:
            logger.error(f"调用解析服务超时: {url} - {e}")
            return False
        except httpx.ConnectError as e:
            logger.error(f"连接解析服务失败（请确认服务已启动且地址正确）: {url} - {e}")
            return False
        except Exception as e:
            logger.error(f"调用解析服务失败: {url} - {e}", exc_info=True)
            return False

    async def upload_file_for_parse_async(
        self,
        file_content: bytes,
        filename: str,
        doc_id: str,
        index: Optional[str] = None,
        knowledge_base_name: Optional[str] = None,
        embedding_base_url: Optional[str] = None,
        embedding_model: Optional[str] = None,
    ) -> bool:
        """
        将文件内容上传到解析服务，由解析服务保存后解析、向量化并写入 ES。
        index 应为知识库的 es_id（或 linkrag_kb_{id}），解析后的切片会写入该索引。
        若提供 embedding_base_url，解析服务将使用该地址做向量化，避免 config.yml 与页面不一致导致解析报错。
        """
        url = f"{self.base_url}{self._upload_file_path}"
        index_val = index or self.es_index
        data = {"id": doc_id, "index": index_val}
        if knowledge_base_name is not None:
            data["knowledge_base_name"] = knowledge_base_name
        if embedding_base_url:
            data["embedding_base_url"] = embedding_base_url
        if embedding_model:
            data["embedding_model"] = embedding_model
        logger.info(f"调用解析服务(上传文件): POST {url}  doc_id={doc_id}, filename={filename}, index={index_val}")
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    url,
                    files={"file": (filename, file_content)},
                    data=data,
                )
            if resp.status_code in SUCCESS_STATUS_CODES:
                logger.info(
                    f"解析任务已提交(上传文件): doc_id={doc_id}, filename={filename}, status={resp.status_code}"
                )
                return True
            logger.warning(
                f"解析服务返回异常: status={resp.status_code}, body={resp.text!r}"
            )
            return False
        except httpx.TimeoutException as e:
            logger.error(f"调用解析服务超时: {url} - {e}")
            return False
        except httpx.ConnectError as e:
            logger.error(f"连接解析服务失败（请确认服务已启动且地址正确）: {url} - {e}")
            return False
        except Exception as e:
            logger.error(f"调用解析服务失败: {url} - {e}", exc_info=True)
            return False

    async def upload_file_stream_async(
        self,
        file_content: bytes,
        filename: str,
        doc_id: str,
        index: Optional[str] = None,
    ) -> bool:
        """调用解析服务 /file/upload_stream 上传文件并异步解析入库。"""
        url = f"{self.base_url}{self._upload_stream_path}"
        index_val = index or self.es_index
        data = {"doc_id": doc_id, "id": doc_id, "index": index_val}
        logger.info(f"调用解析服务(流式上传): POST {url} doc_id={doc_id}, filename={filename}, index={index_val}")
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    url,
                    files={"file": (filename, file_content)},
                    data=data,
                )
            if resp.status_code in SUCCESS_STATUS_CODES:
                logger.info(
                    f"解析任务已提交(流式上传): doc_id={doc_id}, filename={filename}, status={resp.status_code}"
                )
                return True
            logger.warning(
                f"解析服务返回异常(流式上传): status={resp.status_code}, body={resp.text!r}"
            )
            return False
        except httpx.TimeoutException as e:
            logger.error(f"调用解析服务超时(流式上传): {url} - {e}")
            return False
        except httpx.ConnectError as e:
            logger.error(f"连接解析服务失败(流式上传): {url} - {e}")
            return False
        except Exception as e:
            logger.error(f"调用解析服务失败(流式上传): {url} - {e}", exc_info=True)
            return False

    async def upload_for_parse_async(
        self,
        filepath: str,
        doc_id: str,
        index: Optional[str] = None,
        embedding_base_url: Optional[str] = None,
        embedding_model: Optional[str] = None,
    ) -> bool:
        """异步提交「按服务器路径解析并入库」任务（路径须在解析服务机器可访问）。"""
        url = f"{self.base_url}{self._upload_path}"
        payload = self._build_payload(
            filepath, doc_id, index,
            embedding_base_url=embedding_base_url,
            embedding_model=embedding_model,
        )
        logger.info(f"调用解析服务: POST {url}  payload={payload}")
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=payload)
            if resp.status_code in SUCCESS_STATUS_CODES:
                logger.info(
                    f"解析任务已提交: filepath={filepath}, doc_id={doc_id}, index={payload['index']}, status={resp.status_code}"
                )
                return True
            logger.warning(
                f"解析服务返回异常: status={resp.status_code}, body={resp.text!r}"
            )
            return False
        except httpx.TimeoutException as e:
            logger.error(f"调用解析服务超时: {url} - {e}")
            return False
        except httpx.ConnectError as e:
            logger.error(f"连接解析服务失败（请确认服务已启动且地址正确）: {url} - {e}")
            return False
        except Exception as e:
            logger.error(f"调用解析服务失败: {url} - {e}", exc_info=True)
            return False

    async def create_index_async(self, index: str) -> bool:
        """在解析服务侧创建 ES 索引（先查 /index/info，存在则直接成功，不存在再调 /index/create）"""
        # 先通过 /index/info 判断是否已存在（对应 docs#/index/info_index_info_post）
        info_url = f"{self.base_url}{self._index_info_path}"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                info_resp = await client.post(info_url, json={"index": index})
            if info_resp.status_code == 200:
                info_data = info_resp.json() if info_resp.headers.get("content-type", "").startswith("application/json") else {}
                if info_data.get("status") == 200:
                    logger.info(f"ES 索引已存在: {index}")
                    return True
        except Exception as e:
            logger.warning(f"查询索引信息失败，继续尝试创建: {info_url} - {e}")

        url = f"{self.base_url}{self._index_create_path}"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.put(url, json={"index": index})
            if resp.status_code == 200:
                data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                if data.get("status") == 200:
                    logger.info(f"ES 索引已创建或已存在: {index}")
                    return True
                logger.warning(f"创建索引返回异常: {data}")
                return False
            logger.warning(f"创建索引失败: status={resp.status_code}, body={resp.text!r}")
            return False
        except Exception as e:
            logger.error(f"解析服务侧创建索引失败（请确认解析服务已启动且地址可访问）: {url} - {e}", exc_info=True)
            return False

    async def delete_index_async(self, index: str) -> bool:
        """在解析服务侧删除 ES 索引（与 src/server/db.py DELETE /index/delete 对应）"""
        url = f"{self.base_url}{self._index_delete_path}"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.request("DELETE", url, json={"index": index})
            if resp.status_code == 200:
                data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                if data.get("status") == 200:
                    logger.info(f"ES 索引已删除或不存在: {index}")
                    return True
                logger.warning(f"删除索引返回异常: {data}")
                return False
            logger.warning(f"删除索引失败: status={resp.status_code}, body={resp.text!r}")
            return False
        except Exception as e:
            logger.error(f"解析服务侧删除索引失败（请确认解析服务已启动且地址可访问）: {url} - {e}", exc_info=True)
            return False

    async def delete_doc_chunks_async(self, index: str, doc_id: str) -> bool:
        """在解析服务侧按 doc_id 删除索引中的文档切片（/index/delete-doc）。"""
        url = f"{self.base_url}{self._index_delete_doc_path}"
        payload = {"index": index, "doc_id": doc_id}
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                if data.get("status") == 200:
                    logger.info(f"ES 文档切片已删除或无需删除: index={index}, doc_id={doc_id}")
                    return True
                logger.warning(f"删除文档切片返回异常: {data}")
                return False
            logger.warning(f"删除文档切片失败: status={resp.status_code}, body={resp.text!r}")
            return False
        except Exception as e:
            logger.error(f"解析服务侧删除文档切片失败: {url} - {e}", exc_info=True)
            return False

    async def update_text_pipeline_async(
        self,
        index: str,
        chunk_size: int,
        chunk_overlap: int,
        chunk_strategy: str,
    ) -> bool:
        """更新解析服务中某知识库索引对应的文本切分参数（/api/update_text_pipeline）。"""
        url = f"{self.base_url}{self._update_text_pipeline_path}"
        payload = {
            "index": index,
            "chunk_size": int(chunk_size),
            "chunk_overlap": int(chunk_overlap),
            "chunk_strategy": (chunk_strategy or "general").strip() or "general",
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                if data.get("status") == 200:
                    logger.info(
                        f"解析参数已更新: index={index}, chunk_size={chunk_size}, chunk_overlap={chunk_overlap}, chunk_strategy={payload['chunk_strategy']}"
                    )
                    return True
                logger.warning(f"更新解析参数返回异常: {data}")
                return False
            logger.warning(f"更新解析参数失败: status={resp.status_code}, body={resp.text!r}")
            return False
        except Exception as e:
            logger.error(f"调用解析服务更新解析参数失败: {url} - {e}", exc_info=True)
            return False
