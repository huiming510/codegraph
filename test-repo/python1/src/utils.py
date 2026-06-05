# -*- coding: utf-8 -*-
"""
# @Time    : 2025/11/28 13:18
# @Author  : cuils
# @Description:
"""
import yaml
import json
import uuid
import time
import queue
import logging
import datetime
import threading
from elasticsearch import Elasticsearch
from elasticsearch.helpers import streaming_bulk, BulkIndexError


def load_config(config_path: str):
    with open(config_path, encoding="utf8") as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    return config


ES_MAPPINGS = {
    "properties": {
        "uid": {"type": "keyword"},  # 请求id
        "level": {"type": "keyword"},  # 日志等级
        "logger_name": {"type": "keyword"}, # 日志logger名称，用于区分不同的应用
        "status": {"type": "keyword"},  # 返回状态
        "request": {"type": "object"},  # 请求内容
        "response": {"type": "object", "enabled": False},  # 返回内容
        "extra": {"type": "object", "enabled": False}, # 其他信息
        "timestamp": {"type": "date", "format": "yyyy-MM-dd HH:mm:ss||strict_date_optional_time||epoch_millis"} # 记录时间戳
    }
}

ES_SETTINGS = {
    "number_of_shards": 1,
    "number_of_replicas": 0,
    "index.refresh_interval": "30s"
}


class ElasticsearchHandler(logging.Handler):
    def __init__(
            self, hosts='http://localhost:9200', index='python-logs-%Y.%m.%d',
            verify_certs=False, buffer_size=100, interval=5
    ):
        super().__init__()
        self.index = index
        self.buffer_size = buffer_size
        self.interval = interval
        self._q = queue.Queue(maxsize=10000)
        self._stop = threading.Event()

        # 初始化
        self.es = Elasticsearch(
            hosts,
            verify_certs=verify_certs,
            request_timeout=30
        )
        # 判断索引是否存在，如果不存在则新建索引
        if not self.es.indices.exists(index=self.index):
            self.es.indices.create(index=self.index, body={"mappings": ES_MAPPINGS, "settings": ES_SETTINGS})
            time.sleep(5)  # 手动阻塞一下

        if not self.es.indices.exists(index=self.index):
            raise RuntimeError(f"Index {self.index} does not exist, create failed, please check it!")

        # 启动后台线程
        self._thread = threading.Thread(target=self._background, daemon=True)
        self._thread.start()

    def _background(self):
        """后台线程：攒够 bulk_size 或超时 flush_sec 就批量写入"""
        buffer = []
        last = time.time()
        while not self._stop.is_set():
            try:
                doc = self._q.get(timeout=0.5)
            except queue.Empty:
                pass
            else:
                buffer.append(doc)
            now = time.time()
            if buffer and (len(buffer) >= self.buffer_size or now - last >= self.interval):
                self.upload(buffer)
                buffer, last = [], now
        # 收尾
        if buffer:
            self.upload(buffer)

    def upload(self, buffer: list[dict]):
        """真正写 ES"""

        def gen():
            for doc in buffer:
                _id = str(uuid.uuid4())
                yield {"_index": self.index, "_id": _id, "_source": doc}

        try:
            for status, info in streaming_bulk(self.es, actions=gen(), max_retries=3):
                if not status:
                    print(f"es upload failed. {info}")
        except BulkIndexError as e:
            for item in e.errors:
                print(item)

    def emit(self, record: logging.LogRecord):
        log = json.loads(record.getMessage())
        doc = {
            "uid": log.get("uid") or log.get("session_id"),
            "level": record.levelname,
            "logger_name": record.name,
            "status": log.get("status"),
            "request": log.get("request"),
            "response": log.get("response"),
            "extra": log.get("extra"),
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        try:
            self._q.put(doc, block=False)
            self.flush()
        except queue.Full:
            # 队列满了直接丢弃，防止阻塞业务
            self.handleError(record)

    def close(self):
        self._stop.set()
        self._thread.join(timeout=10)
        super().close()


def get_logger(name="log", log_file=None, add_es=False, es_hosts=None):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    # logger.handlers.clear()
    formatter = logging.Formatter("[%(levelname)s %(filename)s:%(lineno)s]: %(message)s")
    file_handler = logging.FileHandler(log_file, encoding="utf8", mode="w")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    if add_es and es_hosts:
        es_handler = ElasticsearchHandler(
            hosts=es_hosts,
            index="app_log",
            interval=5
        )
        logger.addHandler(es_handler)
    return logger