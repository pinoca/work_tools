# -*- coding: utf-8 -*-
import threading
import os
import time
import http.server
import sys
from modules import rest_server
import importlib
import argparse

import_recode_dict = {}
init_import_list = []
# 项目根目录
path = os.path.dirname(__file__)


def hot_deployment():
    while True:
        time.sleep(0.5)
        try:
            # 获取现在的列表
            for hot_namespace, hot_value in sys.modules.items():
                try:
                    if hot_namespace not in init_import_list:
                        try:
                            try:
                                namespace_path = hot_value.__path__._path[0].replace("\\", "/").replace("//", "/").replace("\\\\", "/").replace("////", "/")
                            except:
                                namespace_path = hot_value.__file__.replace("\\", "/").replace("//", "/").replace("\\\\", "/").replace("////", "/")
                            if path in namespace_path:
                                if ".py" in namespace_path:
                                    modify_time = os.path.getmtime(namespace_path)
                                else:
                                    # 修改时间
                                    modify_time = os.path.getmtime(path + "/" + hot_namespace.replace('.', '/'))
                                # 判断空间名称是否被记录
                                if hot_namespace in import_recode_dict:
                                    # 判断修改时间是否一样
                                    if modify_time != import_recode_dict[hot_namespace]:
                                        # 重新载入,重载导入形式
                                        if "." in hot_namespace:
                                            try:
                                                importlib.reload(sys.modules[hot_namespace])
                                                print(f"{hot_namespace} reload")
                                            # 因为某些原因重载失败
                                            except:
                                                pass
                                        else:
                                            try:
                                                importlib.reload(sys.modules[hot_namespace])
                                                print(f"{hot_namespace} reload")
                                            # 因为某些原因重载失败
                                            except:
                                                pass
                                        # 更新最后修改
                                        import_recode_dict[hot_namespace] = modify_time
                                # 没有记录就插入模块最后修改时间
                                else:
                                    import_recode_dict[hot_namespace] = modify_time
                        except  Exception as e:
                            pass
                except Exception as e:
                    pass
        except:
            pass


def run():
    """
    线程守护工具，用于开启子线程和守护线程
    :return:
    """
    try:
        hot_deployment_thread = threading.Thread(target=hot_deployment)
        hot_deployment_thread.start()
        print(f"热部署监控自动更新线程启动")
        while True:
            # 判断线程是否存活，没存活就拉起来
            if not hot_deployment_thread.is_alive():
                hot_deployment_thread = threading.Thread(target=hot_deployment)
                hot_deployment_thread.start()
            time.sleep(5)
    except Exception as e:
        print(f"hot_deployment：run error:{e}")


# 解析参数
parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int, default=81, required=False, help="display an integer,server port")
parser.add_argument("--dev_mode", type=int, default=1, required=False, help="display an integer,server port")
parser.add_argument("--hot_deployment", type=int, default=1, required=False)
opt = parser.parse_args()

# 如果支持热部署则运行热部署程序
if opt.hot_deployment == 1:
    for namespace, value in sys.modules.items():
        init_import_list.append(namespace)
    # 设置完毕后自启动并发记录更新
    run_thread = threading.Thread(target=run)
    run_thread.start()
if opt.dev_mode == 1:
    print("开发模式")
    rest_server.dev_mode = True

address = ("0.0.0.0", opt.port)
# 用ThreadingHttpServer绑定对应的应答类
server = http.server.ThreadingHTTPServer(address, rest_server.WebRequestHandler)
print(f"启动地址{address[0]}:{address[1]}")
# 监听端口 forever()方法使用select.select()循环监听请求，当接收到请求后调用 当监听到请求时，取出请求对象
server.serve_forever()
