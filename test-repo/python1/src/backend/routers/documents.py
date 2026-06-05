"""文档：上传、列表、删除、按服务器路径解析入库"""
import os
import re
import shutil
import hashlib
import json
import uuid as uuid_lib
import mimetypes
from urllib.parse import quote
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Body
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db, crud
from logger import logger
from .common import success_response
from server.client import LinkragServerClient  # 仅用 resolve_kb_index_name

router = APIRouter(prefix="/api", tags=["文档"])

ALLOWED_UPLOAD_EXTENSIONS = {
    "pdf",
    "doc",
    "docx",
    "wps",
    "odt",
    "rtf",
    "xls",
    "xlsx",
    "xlsm",
    "xlt",
    "xltx",
    "xltm",
    "csv",
    "ppt",
    "pptx",
    "pps",
    "ppsx",
    "pot",
    "potx",
    "txt",
    "md",
    "markdown",
    "log",
    "json",
    "yaml",
    "yml",
    "xml",
    "html",
    "htm",
    "css",
    "scss",
    "less",
    "js",
    "jsx",
    "ts",
    "tsx",
    "vue",
    "py",
    "java",
    "c",
    "cc",
    "cpp",
    "h",
    "hpp",
    "go",
    "rs",
    "php",
    "rb",
    "sh",
    "bat",
    "ps1",
    "sql",
}


def _get_extension(filename: str) -> str:
    return Path(filename).suffix.lstrip(".").lower() if filename and "." in filename else ""


def _is_allowed_filetype(filename: str) -> bool:
    ext = _get_extension(filename)
    return ext in ALLOWED_UPLOAD_EXTENSIONS

def _sanitize_relative_path(filename: str) -> str:
    """清理路径，防止目录穿越，但保留目录结构（只用/分隔）"""
    if not filename:
        return "unnamed"
    normalized = filename.replace("\\", "/")
    while normalized.startswith("/"):
        normalized = normalized[1:]
    parts = [p for p in normalized.split("/") if p and p not in ('.', '..')]
    return "/".join(parts) or "unnamed"

# 解析走 server 逻辑：入队 backend 内的 task_queue，不请求外部解析服务与 index/create
def _enqueue_parse_task(
    filepath: str,
    doc_id: str,
    index_name: str,
    embedding_base_url: str | None = None,
    embedding_model: str | None = None,
) -> bool:
    """将解析任务放入 server 的 task_queue，由本进程的 file_worker 处理。成功返回 True。"""
    try:
        from server.component import task_queue
        from server.file import FileRequest
        req = FileRequest(id=doc_id, filepath=filepath, index=index_name)
        if embedding_base_url and str(embedding_base_url).strip():
            req.embedding_base_url = str(embedding_base_url).strip()
        if embedding_model and str(embedding_model).strip():
            req.embedding_model = str(embedding_model).strip()
        task_queue.put_nowait(req)
        return True
    except Exception as e:
        logger.debug(f"入队解析任务失败（将仅入库）: {e}")
        return False

UPLOAD_DIR = settings.upload_dir
os.makedirs(UPLOAD_DIR, exist_ok=True)


async def _get_linkrag_server_url(db: AsyncSession) -> str | None:
    """解析服务地址：DB 非空优先，否则回退 .env（DB 存空值时也使用 .env）"""
    cfg = await crud.get_es_config(db)
    db_val = cfg.get("linkrag_server_url") if "linkrag_server_url" in cfg else None
    raw = (db_val or "").strip() or (settings.linkrag_server_url or "").strip()
    return raw or None


def _safe_dirname(name: str) -> str:
    """将知识库名等转为可作目录名的字符串（去除路径非法字符）"""
    if not name or not name.strip():
        return "default"
    s = re.sub(r'[<>:"/\\|?*]', "_", name.strip())
    return s[:100] or "default"


def get_file_hash(file_path: str) -> str:
    """计算文件哈希"""
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _form_bool(val) -> bool:
    """表单字段转 bool：支持 True/true/1/yes 等"""
    if val is True or val is False:
        return bool(val)
    if isinstance(val, str):
        return val.strip().lower() in ("true", "1", "yes", "on")
    return False


def _guess_media_type(file_path: str) -> str:
    media_type, _ = mimetypes.guess_type(file_path)
    return media_type or "application/octet-stream"


def _content_disposition(filename: str, inline: bool = False) -> str:
    disposition = "inline" if inline else "attachment"
    return f"{disposition}; filename*=UTF-8''{quote(filename)}"


def _remote_doc_id(doc) -> str:
    """生成提交给 linkrag server 的稳定唯一 doc_id，避免远端因重复主键返回 500。"""
    ts = int(doc.created_at.timestamp() * 1000) if getattr(doc, "created_at", None) else 0
    return f"{doc.id}_{ts}"


async def _upload_single_file(
    file: UploadFile,
    knowledge_base_id: int,
    kb,
    db: AsyncSession,
    tags: str = "",
    tags_list: Optional[list[str]] = None,
    skip_parse_bool: bool = False,
    relative_filename: Optional[str] = None,
) -> dict:
    """处理单个文件上传并返回结果明细。"""
    raw_filename = relative_filename if relative_filename else file.filename
    safe_filename = _sanitize_relative_path(raw_filename)
    if not _is_allowed_filetype(safe_filename):
        ext = _get_extension(safe_filename) or "unknown"
        return {
            "success": False,
            "message": f"不支持的文件类型: .{ext}",
            "file_info": {
                "filename": safe_filename,
                "status": "failed",
            },
        }

    # 按 知识库名/uuid/文件名 创建目录并保存（使用文件系统安全的路径）
    kb_dir = _safe_dirname(kb.name)
    upload_uuid = str(uuid_lib.uuid4())
    sub_dir = Path(UPLOAD_DIR) / kb_dir / upload_uuid
    file_path = sub_dir / safe_filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    file_path_str = str(file_path.resolve())

    content_hash = get_file_hash(file_path_str)
    existing = await crud.get_document_by_hash(db, content_hash, kb_id=knowledge_base_id)
    if existing:
        os.remove(file_path_str)
        logger.warning(f"文件已存在: {safe_filename}")
        return {
            "success": False,
            "message": "文件已存在",
            "file_info": {
                "id": existing.id,
                "filename": existing.filename,
                "status": existing.status,
            },
        }

    if tags_list is not None:
        tag_list = [str(t).strip() for t in tags_list if str(t).strip()]
    else:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    file_type = _get_extension(safe_filename) or None

    doc = await crud.create_document(
        db=db,
        knowledge_base_id=knowledge_base_id,
        filename=safe_filename,
        file_path=file_path_str,
        file_size=os.path.getsize(file_path_str),
        file_type=file_type,
        tags=tag_list,
        content_hash=content_hash,
    )
    await crud.update_kb_document_count(db, knowledge_base_id)
    await db.commit()

    if skip_parse_bool:
        await crud.update_document_status(db, doc.id, "completed")
        await db.commit()
        logger.info(f"文件上传后直接标记完成: {safe_filename} | 知识库: {kb.name} | ID: {doc.id}")
    else:
        # 解析与入库统一走外部 linkrag server 接口（其内部会处理 ES）
        index_name = LinkragServerClient.resolve_kb_index_name(kb)
        logger.info(f"提交解析任务(linkrag upload_stream): doc_id={doc.id}, filename={safe_filename}, index={index_name}")
        linkrag_url = await _get_linkrag_server_url(db)
        submitted = False
        if linkrag_url:
            client = LinkragServerClient(base_url=linkrag_url)
            with open(file_path_str, "rb") as f:
                file_bytes = f.read()
            submitted = await client.upload_file_stream_async(
                file_content=file_bytes,
                filename=safe_filename,
                doc_id=_remote_doc_id(doc),
                index=index_name,
            )
        else:
            logger.warning("未配置 linkrag_server_url，无法调用 /file/upload_stream")
        if submitted:
            await crud.update_document_status(db, doc.id, "completed")
            await db.commit()
            logger.info(f"文档已提交并标记入库完成: doc_id={doc.id}")
        else:
            await crud.update_document_status(db, doc.id, "failed")
            await db.commit()
            logger.info("linkrag 上传接口调用失败，文档标记为 failed；请检查 linkrag_server_url 与解析服务状态")

    logger.info(f"文件上传成功: {safe_filename} | 知识库: {kb.name} | ID: {doc.id}")
    return {
        "success": True,
        "message": "文件上传成功",
        "file_info": {
            "id": doc.id,
            "filename": doc.filename,
            "upload_time": doc.created_at.isoformat(),
            "size": doc.file_size,
            "tags": doc.tags,
            "status": doc.status,
        },
    }


@router.post("/upload")
async def upload_file(
    file: Optional[UploadFile] = File(None),
    files: Optional[list[UploadFile]] = File(None),
    knowledge_base_id: int = Form(1),
    tags: str = Form(""),
    file_tags_json: str = Form(""),
    relative_paths_json: str = Form(""),
    skip_parse: str = Form("false"),
    db: AsyncSession = Depends(get_db),
):
    """上传文档到知识库（支持单文件 file 与多文件 files）。"""
    skip_parse_bool = _form_bool(skip_parse)
    try:
        kb = await crud.get_knowledge_base(db, knowledge_base_id)
        if not kb:
            raise HTTPException(status_code=404, detail="知识库不存在")

        upload_items: list[UploadFile] = []
        if file is not None:
            upload_items.append(file)
        if files:
            upload_items.extend([f for f in files if f is not None])
        if not upload_items:
            raise HTTPException(status_code=400, detail="请至少上传一个文件")

        per_file_tags: dict[str, list[str]] = {}
        if file_tags_json and file_tags_json.strip():
            try:
                raw = json.loads(file_tags_json)
                if isinstance(raw, dict):
                    for k, v in raw.items():
                        name = _sanitize_relative_path(str(k))
                        if isinstance(v, list):
                            per_file_tags[name] = [str(t) for t in v]
                        elif isinstance(v, str):
                            per_file_tags[name] = [x.strip() for x in v.split(",") if x.strip()]
            except Exception:
                logger.warning("file_tags_json 解析失败，回退使用 tags 字段")

        relative_paths: list[str] = []
        if relative_paths_json and relative_paths_json.strip():
            try:
                raw_paths = json.loads(relative_paths_json)
                if isinstance(raw_paths, list):
                    relative_paths = [_sanitize_relative_path(str(path)) for path in raw_paths]
            except Exception:
                logger.warning("relative_paths_json 解析失败，回退使用上传文件名")

        results = []
        for idx, item in enumerate(upload_items):
            preferred_name = relative_paths[idx] if idx < len(relative_paths) else None
            try:
                current_name = preferred_name or (_sanitize_relative_path(item.filename) if item and item.filename else "")
                current_tags = per_file_tags.get(current_name)
                result = await _upload_single_file(
                    file=item,
                    knowledge_base_id=knowledge_base_id,
                    kb=kb,
                    db=db,
                    tags=tags,
                    tags_list=current_tags,
                    skip_parse_bool=skip_parse_bool,
                    relative_filename=preferred_name,
                )
            except Exception as e:
                safe_filename = preferred_name or (_sanitize_relative_path(item.filename) if item and item.filename else "unnamed")
                logger.error(f"文件上传失败: {safe_filename} - {e}", exc_info=True)
                result = {
                    "success": False,
                    "message": f"文件上传失败: {e}",
                    "file_info": {"filename": safe_filename, "status": "failed"},
                }
            results.append(result)

        if len(results) == 1:
            msg = results[0].get("message") or ("文件上传成功" if results[0].get("success") else "文件上传失败")
            return success_response(data=results[0], msg=msg)

        success_count = sum(1 for r in results if r.get("success"))
        failed_count = len(results) - success_count
        message = f"批量上传完成：成功 {success_count}，失败 {failed_count}"
        return success_response(
            data={
                "success": failed_count == 0,
                "message": message,
                "total": len(results),
                "success_count": success_count,
                "failed_count": failed_count,
                "results": results,
            },
            msg=message,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ParseStatusCallbackBody(BaseModel):
    """解析服务完成后的回调 body"""
    status: str  # completed | failed
    chunk_count: int = 0
    message: str = ""


class IngestByPathRequest(BaseModel):
    """按服务器文件路径解析并入库请求"""
    file_path: str
    knowledge_base_id: int = 1
    tags: list = []


@router.post("/ingest-by-path")
async def ingest_by_path(
    body: IngestByPathRequest = Body(...),
    db: AsyncSession = Depends(get_db),
):
    """
    通过服务器上的文件路径进行解析并入库。
    若配置了 linkrag_server_url，会调用解析服务进行解析与向量化；否则仅创建文档记录并回显。
    """
    try:
        kb = await crud.get_knowledge_base(db, body.knowledge_base_id)
        if not kb:
            raise HTTPException(status_code=404, detail="知识库不存在")

        path = Path(body.file_path).resolve()
        if not path.exists():
            raise HTTPException(status_code=400, detail=f"文件不存在: {body.file_path}")
        if not path.is_file():
            raise HTTPException(status_code=400, detail="路径必须是文件")

        filename = path.name
        if not _is_allowed_filetype(filename):
            ext = _get_extension(filename) or "unknown"
            raise HTTPException(status_code=400, detail=f"不支持的文件类型: .{ext}")
        file_type = path.suffix.lstrip(".").lower() if path.suffix else None
        file_size = path.stat().st_size
        file_path_str = str(path)

        tag_list = [t.strip() for t in body.tags if t and isinstance(t, str)] if body.tags else []
        if isinstance(body.tags, list) and body.tags and isinstance(body.tags[0], dict):
            tag_list = [t.get("value") or t.get("label") or str(t) for t in body.tags if t]

        doc = await crud.create_document(
            db=db,
            knowledge_base_id=body.knowledge_base_id,
            filename=filename,
            file_path=file_path_str,
            file_size=file_size,
            file_type=file_type,
            tags=tag_list,
            content_hash=None,
        )
        await crud.update_kb_document_count(db, body.knowledge_base_id)
        await db.commit()

        # 解析走外部 linkrag server /file/upload（按服务器路径）
        index_name = LinkragServerClient.resolve_kb_index_name(kb)
        linkrag_url = await _get_linkrag_server_url(db)
        submitted = False
        if linkrag_url:
            client = LinkragServerClient(base_url=linkrag_url)
            submitted = await client.upload_for_parse_async(
                filepath=file_path_str,
                doc_id=_remote_doc_id(doc),
                index=index_name,
            )
        else:
            logger.warning("未配置 linkrag_server_url，无法调用 /file/upload")
        if submitted:
            await crud.update_document_status(db, doc.id, "completed")
            await db.commit()
        else:
            await crud.update_document_status(db, doc.id, "failed")
            await db.commit()
            logger.info("linkrag 上传接口调用失败，文档标记为 failed")

        logger.info(f"按路径入库成功: {filename} | 知识库: {kb.name} | ID: {doc.id}")

        return success_response(
            data={
                "success": True,
                "message": "解析并入库成功",
                "file_info": {
                    "id": doc.id,
                    "filename": doc.filename,
                    "upload_time": doc.created_at.isoformat(),
                    "size": doc.file_size,
                    "tags": doc.tags or [],
                    "status": doc.status,
                },
            },
            msg="解析并入库成功",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"按路径入库失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/{doc_id}/parse-status")
async def update_parse_status(
    doc_id: int,
    body: ParseStatusCallbackBody = Body(...),
    db: AsyncSession = Depends(get_db),
):
    """
    解析服务完成后回调，更新文档解析状态。
    由 linkrag 解析服务在解析成功/失败时调用。
    """
    doc = await crud.get_document(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    if body.status not in ("completed", "failed"):
        raise HTTPException(status_code=400, detail="status 必须为 completed 或 failed")
    await crud.update_document_status(
        db, doc_id, body.status,
        chunk_count=body.chunk_count if body.status == "completed" else None,
    )
    await db.commit()
    logger.info(f"文档解析状态已更新: doc_id={doc_id}, status={body.status}, chunk_count={body.chunk_count}")
    return success_response(data={"success": True}, msg="状态已更新")


@router.post("/documents/{doc_id}/trigger-parse")
async def trigger_parse(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    对「待处理/仅入库（历史状态）」或「解析失败」的文档触发解析流程：调用 linkrag server 解析接口。
    仅当文档状态为 pending / uploaded（历史兼容）/ failed 时可用。
    """
    doc = await crud.get_document(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    if doc.status not in ("pending", "uploaded", "failed"):
        raise HTTPException(
            status_code=400,
            detail=f"仅支持对「待处理/未解析」或「解析失败」的文档触发解析，当前状态: {doc.status}",
        )
    if not os.path.isfile(doc.file_path):
        raise HTTPException(status_code=400, detail=f"文件不存在: {doc.file_path}")

    kb = await crud.get_knowledge_base(db, doc.knowledge_base_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    try:
        index_name = LinkragServerClient.resolve_kb_index_name(kb)
        linkrag_url = await _get_linkrag_server_url(db)
        submitted = False
        if linkrag_url:
            client = LinkragServerClient(base_url=linkrag_url)
            submitted = await client.upload_for_parse_async(
                filepath=doc.file_path,
                doc_id=_remote_doc_id(doc),
                index=index_name,
            )
        else:
            logger.warning("未配置 linkrag_server_url，无法调用 /file/upload")
        if submitted:
            await crud.update_document_status(db, doc.id, "completed")
            await db.commit()
            logger.info(f"已触发解析: doc_id={doc_id}, filename={doc.filename}")
            return success_response(
                data={"success": True, "message": "已提交并标记入库完成"},
                msg="已入库完成",
            )
        await crud.update_document_status(db, doc.id, "failed")
        await db.commit()
        raise HTTPException(status_code=502, detail="解析服务调用失败，请确认 linkrag_server_url 与解析服务状态")
    except HTTPException:
        raise
    except Exception as e:
        await crud.update_document_status(db, doc.id, "failed")
        await db.commit()
        logger.exception(f"触发解析失败: doc_id={doc_id}, error={e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents")
async def get_documents(
    knowledge_base_id: int = None,
    search: str = None,
    db: AsyncSession = Depends(get_db),
):
    """获取文档列表。search: 仅按文件名模糊检索，不按知识库名。"""
    docs = await crud.get_documents(
        db, knowledge_base_id=knowledge_base_id, limit=500, search=search
    )
    return success_response(
        data={
            "documents": [
                {
                    "id": doc.id,
                    "knowledge_base_id": doc.knowledge_base_id,
                    "filename": doc.filename,
                    "upload_time": doc.created_at.isoformat(),
                    "size": doc.file_size,
                    "tags": doc.tags or [],
                    "status": doc.status,
                    "chunk_count": doc.chunk_count or 0,
                }
                for doc in docs
            ]
        }
    )


@router.get("/documents/{doc_id}/view")
async def view_document(doc_id: int, db: AsyncSession = Depends(get_db)):
    """在线查看文档（浏览器内联打开）。"""
    doc = await crud.get_document(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    if not os.path.isfile(doc.file_path):
        raise HTTPException(status_code=404, detail="文件不存在或已被删除")
    return FileResponse(
        path=doc.file_path,
        media_type=_guess_media_type(doc.file_path),
        headers={"Content-Disposition": _content_disposition(doc.filename, inline=True)},
    )


@router.get("/documents/{doc_id}/download")
async def download_document(doc_id: int, db: AsyncSession = Depends(get_db)):
    """下载文档。"""
    doc = await crud.get_document(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    if not os.path.isfile(doc.file_path):
        raise HTTPException(status_code=404, detail="文件不存在或已被删除")
    return FileResponse(
        path=doc.file_path,
        media_type="application/octet-stream",
        headers={"Content-Disposition": _content_disposition(doc.filename, inline=False)},
    )


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: int, db: AsyncSession = Depends(get_db)):
    """删除文档（同时删除 ES 中该文档对应的切片）"""
    doc = await crud.get_document(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 通过解析服务删除 ES 中该文档的切片
    linkrag_url = await _get_linkrag_server_url(db)
    kb = await crud.get_knowledge_base(db, doc.knowledge_base_id)
    if linkrag_url and kb:
        try:
            client = LinkragServerClient(base_url=linkrag_url)
            index_name = LinkragServerClient.resolve_kb_index_name(kb)
            await client.delete_doc_chunks_async(index_name, _remote_doc_id(doc))
        except Exception as e:
            logger.warning(f"删除文档时调用解析服务删除切片失败: doc_id={doc_id}, error={e}")
    elif not linkrag_url:
        logger.warning(f"未配置 linkrag_server_url，跳过删除文档切片: doc_id={doc_id}")

    # 仅删除位于上传目录内的文件，避免删除通过「服务器路径」入库的原始文件
    upload_abs = os.path.abspath(UPLOAD_DIR)
    if os.path.exists(doc.file_path) and os.path.abspath(doc.file_path).startswith(upload_abs):
        os.remove(doc.file_path)

    await crud.delete_document(db, doc_id)
    logger.info(f"文档已删除: {doc.filename} | ID: {doc_id}")
    return success_response(data={"success": True}, msg="文档删除成功")


# ==================== 文档管理：虚拟文件夹与归属（后端存储，换机同步） ====================

class VirtualFolderCreateBody(BaseModel):
    id: str
    name: str
    parent_key: str  # kb-{id} 或 vf-{id}
    kb_id: int


class AssignmentsBody(BaseModel):
    assignments: dict  # { "docId": "parentKey", ... }


@router.get("/doc-folders/virtual-folders")
async def list_virtual_folders(
    knowledge_base_id: int = None,
    db: AsyncSession = Depends(get_db),
):
    """获取虚拟文件夹列表，可选按知识库筛选"""
    rows = await crud.get_virtual_folders(db, kb_id=knowledge_base_id)
    return success_response(
        data={
            "virtual_folders": [
                {
                    "id": r.id,
                    "name": r.name,
                    "parentKey": r.parent_key,
                    "kbId": r.kb_id,
                }
                for r in rows
            ]
        }
    )


@router.post("/doc-folders/virtual-folders")
async def create_virtual_folder(
    body: VirtualFolderCreateBody = Body(...),
    db: AsyncSession = Depends(get_db),
):
    """创建虚拟文件夹"""
    kb = await crud.get_knowledge_base(db, body.kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    if await crud.get_virtual_folder(db, body.id):
        raise HTTPException(status_code=400, detail="该 id 已存在")
    await crud.create_virtual_folder(
        db, id=body.id, name=body.name, parent_key=body.parent_key, kb_id=body.kb_id
    )
    await db.commit()
    return success_response(data={"id": body.id}, msg="创建成功")


@router.delete("/doc-folders/virtual-folders/{vf_id}")
async def delete_virtual_folder_route(
    vf_id: str,
    db: AsyncSession = Depends(get_db),
):
    """删除虚拟文件夹（含子孙），并删除该文件夹及其子孙文件夹内的所有文档（库表+磁盘+ES）"""
    vf = await crud.get_virtual_folder(db, vf_id)
    if not vf:
        raise HTTPException(status_code=404, detail="虚拟文件夹不存在")

    # 先查出该文件夹树下的所有文档 id，再逐个完整删除（ES 切片、磁盘文件、数据库）
    doc_ids = await crud.get_document_ids_in_virtual_folder_tree(db, vf_id)
    linkrag_url = await _get_linkrag_server_url(db)
    linkrag_client = LinkragServerClient(base_url=linkrag_url) if linkrag_url else None
    for doc_id in doc_ids:
        doc = await crud.get_document(db, doc_id)
        if not doc:
            continue
        try:
            if linkrag_client:
                kb = await crud.get_knowledge_base(db, doc.knowledge_base_id)
                if kb:
                    index_name = LinkragServerClient.resolve_kb_index_name(kb)
                    await linkrag_client.delete_doc_chunks_async(index_name, _remote_doc_id(doc))
            upload_abs = os.path.abspath(UPLOAD_DIR)
            if os.path.exists(doc.file_path) and os.path.abspath(doc.file_path).startswith(upload_abs):
                os.remove(doc.file_path)
        except Exception as e:
            logger.warning(f"删除文件夹内文档时清理切片/文件失败 doc_id={doc_id}: {e}")
        await crud.delete_document(db, doc_id)

    removed = await crud.delete_virtual_folder(db, vf_id)
    if removed is None:
        raise HTTPException(status_code=404, detail="虚拟文件夹不存在")
    if doc_ids:
        await crud.update_kb_document_count(db, vf.kb_id)
    await db.commit()
    deleted_count = len(doc_ids)
    logger.info(f"已删除虚拟文件夹 vf_id={vf_id}，文件夹数={removed}，同时删除文档数={deleted_count}")
    return success_response(
        data={"removed": removed, "documents_deleted": deleted_count},
        msg=f"已删除文件夹及其中 {deleted_count} 个文档" if deleted_count else "已删除",
    )


@router.get("/doc-folders/assignments")
async def get_folder_assignments_route(
    knowledge_base_id: int = None,
    db: AsyncSession = Depends(get_db),
):
    """获取文档归属：document_id -> parent_key（仅包含在虚拟文件夹内的文档）"""
    data = await crud.get_folder_assignments(db, knowledge_base_id=knowledge_base_id)
    return success_response(data={"assignments": data})


@router.put("/doc-folders/assignments")
async def set_folder_assignments_route(
    body: AssignmentsBody = Body(...),
    db: AsyncSession = Depends(get_db),
):
    """批量设置文档归属。assignments: { "docId": "parentKey" }，parent_key 为 kb- 时表示归到知识库根"""
    if body.assignments and isinstance(body.assignments, dict):
        await crud.set_folder_assignments_batch(db, body.assignments)
    await db.commit()
    return success_response(data={"success": True}, msg="已更新")
