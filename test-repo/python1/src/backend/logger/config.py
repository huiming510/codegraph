"""日志配置"""
import sys
from pathlib import Path
from loguru import logger


def setup_logger():
    """配置日志系统"""
    from config import settings
    
    LOG_LEVEL = settings.log_level
    LOG_DIR = settings.log_dir
    LOG_TO_DB = settings.log_to_db
    LOG_RETENTION_DAYS = settings.log_retention_days
    
    # 日志格式
    LOG_FORMAT = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    LOG_FORMAT_FILE = (
        "{time:YYYY-MM-DD HH:mm:ss} | "
        "{level: <8} | "
        "{name}:{function}:{line} | "
        "{message}"
    )
    
    # 移除默认handler
    logger.remove()
    
    # 控制台输出（彩色）
    logger.add(
        sys.stdout,
        format=LOG_FORMAT,
        level=LOG_LEVEL,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )
    
    # 创建日志目录
    log_path = Path(LOG_DIR)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # 文件输出 - 全部日志
    logger.add(
        log_path / "app_{time:YYYY-MM-DD}.log",
        format=LOG_FORMAT_FILE,
        level=LOG_LEVEL,
        rotation="00:00",  # 每天轮转
        retention=f"{LOG_RETENTION_DAYS} days",
        compression="gz",
        encoding="utf-8",
        backtrace=True,
        diagnose=True,
    )
    
    # 文件输出 - 错误日志
    logger.add(
        log_path / "error_{time:YYYY-MM-DD}.log",
        format=LOG_FORMAT_FILE,
        level="ERROR",
        rotation="00:00",
        retention=f"{LOG_RETENTION_DAYS} days",
        compression="gz",
        encoding="utf-8",
        backtrace=True,
        diagnose=True,
    )
    
    # 数据库输出（如果启用）- 暂时禁用，避免启动时循环依赖
    # if LOG_TO_DB:
    #     logger.add(
    #         db_sink,
    #         format="{message}",
    #         level="INFO",
    #         filter=lambda record: record["level"].name in ("INFO", "WARNING", "ERROR", "CRITICAL"),
    #     )
    
    logger.info(f"日志系统初始化完成 | 级别: {LOG_LEVEL} | 目录: {LOG_DIR} | 数据库: {LOG_TO_DB}")
    
    return logger


async def db_sink(message):
    """数据库日志写入"""
    try:
        from database.connection import AsyncSessionLocal
        from database import crud
        
        record = message.record
        
        async with AsyncSessionLocal() as db:
            await crud.create_system_log(
                db=db,
                level=record["level"].name,
                module=record["name"],
                message=record["message"],
                trace=record.get("exception", {}).get("traceback") if record.get("exception") else None,
                extra=record.get("extra"),
                request_id=record.get("extra", {}).get("request_id"),
                user_id=record.get("extra", {}).get("user_id"),
                ip_address=record.get("extra", {}).get("ip_address"),
            )
            await db.commit()
    except Exception as e:
        # 避免日志写入失败导致循环
        print(f"日志写入数据库失败: {e}")


# 导出logger实例
__all__ = ['setup_logger', 'logger']
