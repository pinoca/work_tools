import base64
from urllib import parse
import bson
import json
import traceback
import os
from datetime import datetime


def format_path(target_path: str):
    """
    格式化路径字符串，由于python字符串读取规则做的防路径错误设计
    path：需要格式化的路径
    """
    res = target_path.replace("\\", "/").replace("//", "/").replace("\\\\", "/").replace("////", "/")
    return res


file_path = format_path(os.path.abspath(__file__))
project_path = file_path[:-12]


def dict_cov_urlpath(data):
    """
    字典转字符串
    :param data: 字典数据
    :return: 返回一个url字符串
    """
    res = ""
    for k, v in data.items():
        res = f"{res}{k}={v}&"
    return res[:-1]


def parse_url(url) -> dict:
    """
    解析url路径为字典
    :param url:
    :return:
    """
    return dict(parse.parse_qsl(parse.urlparse(url).path))


def get_mongoid():
    """
    返回mongodb_id对象
    :return:
    """
    return bson.ObjectId()


def re_dict(var_dict):
    """
    对字典进行反转
    """
    return dict([(v, k) for (k, v) in var_dict.items()])


def base64_encode(data):
    """
    先把字节流加密后转成str
    :param data: 需要加密的字节流
    :return: str
    """
    if isinstance(data, bytes):
        b_data = base64.b64encode(data)
        data = str(b_data)
    data_str = data[2:-1]
    return data_str


def base64_decode(data):
    """
    b64的补码规则。字符串长度必须为4的倍数
    :param data:
    :return:bytes
    """
    missing_padding = 4 - len(data) % 4
    if missing_padding:
        data += '=' * missing_padding
    return base64.b64decode(data)


def logger(level, data):
    """
    :param level: string
    :param data: dict/list/bytes/tuple/string
    :return: string
    """
    global project_path
    global file_path

    if level not in ['critical', 'error', 'warning', 'info', 'debug']:
        raise Exception('logger level type error')
    if data not in ['', None, list(), dict(), set(), tuple(), b'']:
        try:
            if type(data) == bytes:
                data_string = json.dumps(data.decode('utf-8'))
            else:
                data_string = json.dumps(data)
        except Exception as e:
            raise Exception(str(e))
        file, _, _, _ = traceback.extract_stack()[-2]
        file_name = format_path(file)
        base_name_path = file_name.split(".")[0]
        time_path = datetime.today().strftime("/%Y/%m/%d/%H")
        log_path = format_path(base_name_path[:len(project_path)] + "log/" + base_name_path[len(project_path):] + time_path + datetime.today().strftime("/%M") + ".txt")
        log_dir_path = log_path.rsplit("/", 1)[0]
        os.makedirs(log_dir_path, exist_ok=True)
        log_time = time_path[1:].replace("/", "-")
        log_str = f"""{log_time}  level:{level}  {data_string}\n"""
        with open(log_path, 'a+') as f:
            f.write(log_str)
        return True
    else:
        raise Exception('data不可为空')
