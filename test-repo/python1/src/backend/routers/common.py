"""公共工具：统一响应格式等"""


def success_response(data=None, msg: str = "success"):
    """成功时返回统一格式 {code, data, msg}"""
    return {"code": 0, "data": data, "msg": msg}
