"""FastAPI日志中间件"""
import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger


class LoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 生成请求ID
        request_id = str(uuid.uuid4())[:8]
        
        # 获取客户端IP
        client_ip = request.client.host if request.client else "unknown"
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        
        # 记录请求开始
        start_time = time.time()
        
        # 绑定上下文信息
        with logger.contextualize(request_id=request_id, ip_address=client_ip):
            # 记录请求
            logger.info(
                f"请求开始 | {request.method} {request.url.path} | "
                f"IP: {client_ip} | ID: {request_id}"
            )
            
            try:
                response = await call_next(request)
                
                # 计算耗时
                process_time = (time.time() - start_time) * 1000
                
                # 记录响应
                logger.info(
                    f"请求完成 | {request.method} {request.url.path} | "
                    f"状态: {response.status_code} | 耗时: {process_time:.2f}ms | ID: {request_id}"
                )
                
                # 添加响应头
                response.headers["X-Request-ID"] = request_id
                response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
                
                return response
                
            except Exception as e:
                process_time = (time.time() - start_time) * 1000
                logger.error(
                    f"请求异常 | {request.method} {request.url.path} | "
                    f"错误: {str(e)} | 耗时: {process_time:.2f}ms | ID: {request_id}"
                )
                raise


def get_request_id(request: Request) -> str:
    """从请求中获取请求ID"""
    return request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])


def get_client_ip(request: Request) -> str:
    """获取客户端IP"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
