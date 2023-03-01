# coding=utf-8
import os.path
import sys
import http.server
import json
from urllib import parse

gl_rest_path = 'rest'

url_map_dict = {}

dev_mode = False


class WebRequestHandler(http.server.BaseHTTPRequestHandler):

    # def do_HEAD(self):
    def do_OPTIONS(self):
        print("do_OPTIONS")
        self.send_response_only(200, "ok")
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', '*')
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_FETCH(self):
        print('do_FETCH')
        self.send_response_only(200, "ok")
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', '*')
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def see_dev_mode(self, e):
        if dev_mode:
            raise e

    def do_POST(self):  # token/get_token?sdafdsa=1&213=22
        # 请求路径
        req_path = self.path.split("?")[0].split("/")[1:]
        req_path_str = self.path.split("?")[0]
        url = self.address_string() + self.path
        headers = dict(self.headers)
        # 尝试拿到url连接里的参数数据
        try:
            get_req_datas = self.path.split("?")[1]
            if get_req_datas != '':
                get_req_datas = dict(parse.parse_qsl(parse.urlparse(get_req_datas).path))
                # get_req_datas = json.dumps(dict(parse.parse_qsl(parse.urlparse(get_req_datas).path)))
            else:
                get_req_datas = {}
        except Exception as e:
            get_req_datas = {}
        # 尝试拿到post核载数据
        try:
            post_req_datas = self.rfile.read(int(self.headers['content-length']))
            if isinstance(post_req_datas, bytes):
                post_req_datas = post_req_datas.decode()
            if isinstance(post_req_datas, str):
                if "&" in post_req_datas:
                    post_req_datas = json.dumps(dict(parse.parse_qsl(parse.urlparse(post_req_datas).path)))
            if isinstance(post_req_datas, dict):
                post_req_datas = json.dumps(post_req_datas)
        except Exception as e:
            post_req_datas = {}
        # 如果路径是则去到首页
        if not req_path[0]:
            if gl_rest_path + "index" not in sys.modules:
                try:
                    exec(f"import {gl_rest_path}", globals())
                    exec(f"from {gl_rest_path} import index", globals())
                except Exception as e:
                    res_info = f"模块{gl_rest_path},错误信息：{e}"
                    res = {"static": "1", "info": res_info}
                    self.see_dev_mode(e)
                    return self.showError(res)
            try:
                res_status, res = eval(f"{gl_rest_path}.index.default_index()")
                if res_status == "json":
                    return self.showSuccess(res)
                elif res_status == "text/html":
                    return self.showHtml(res)
            except Exception as e:
                res_info = f"模块{gl_rest_path},错误信息：{e}"
                res = {"static": "1", "info": res_info}
                self.see_dev_mode(e)
                return self.showError(res)
        else:
            if not os.path.exists(os.path.dirname(__file__) + '/../rest/' + req_path[0] + '.py'):
                # print('404', self.path)
                return self.showStatus(404)
        # 加载指定文件夹模块
        if gl_rest_path not in sys.modules:
            try:
                exec(f"import {gl_rest_path}", globals())
                exec(f"from {gl_rest_path} import index", globals())
            except Exception as e:
                res_info = f"模块{gl_rest_path},错误信息：{e}"
                res = {"static": "1", "info": res_info}
                self.see_dev_mode(e)
                return self.showError(res)
        if f"{gl_rest_path}.{req_path[0]}" not in sys.modules:
            try:
                exec(f"from {gl_rest_path} import {req_path[0]}", globals())
            except Exception as e:
                res_info = f"模块{gl_rest_path}.{req_path[0]},错误信息：{e}"
                res = {"static": "1", "info": res_info}
                self.see_dev_mode(e)
                return self.showError(res)
        # 执行模块方法
        try:
            # 查询映射表
            try:
                url_map = eval(f"{gl_rest_path}.{req_path[0]}.url_maps")
                url_map_dict.update(url_map)
            except Exception as e:
                if str(e) == f"""module '{gl_rest_path}.{req_path[0]}' has no attribute 'url_maps'""":
                    pass
                else:
                    self.see_dev_mode(e)
                    self.showError(f"模块{gl_rest_path}.{req_path[0]} 错误信息：{e}")
            if req_path_str in url_map_dict:
                res_status, res = eval(f"""url_map_dict["{req_path_str}"](url=\"{url}\",path=\"{req_path_str}\",get=\"\"\"{get_req_datas}\"\"\",post=\"\"\"{post_req_datas}\"\"\",headers={headers})""")
            else:
                res_status, res = eval(f"{gl_rest_path}.{req_path[0]}.{req_path[1]}(url=\"{url}\",path=\"{req_path_str}\",get=\"\"\"{get_req_datas}\"\"\",post=\"\"\"{post_req_datas}\"\"\",headers={headers})")
        except Exception as e:
            res_info = f"模块{gl_rest_path}.{req_path[0]}.{req_path[1]}错误信息：{e}"
            res = {"static": "1", "info": res_info}
            self.see_dev_mode(e)
            return self.showError(res)
        if res_status == "json":
            self.showSuccess(res)
        elif res_status == "text/html":
            self.showHtml(res)
        elif res_status == "text/plain":
            self.showPlain(res)

    def do_GET(self):
        # 请求路径
        req_path = self.path.split("?")[0].split("/")[1:]
        url = "http://" + self.address_string() + self.path
        headers = dict(self.headers)
        req_path_str = self.path.split("?")[0]
        # 尝试拿到url连接里的参数数据
        try:
            get_req_datas = self.path.split("?")[1]
            if get_req_datas != '':
                get_req_datas = dict(parse.parse_qsl(parse.urlparse(get_req_datas).path))
                # get_req_datas = json.dumps(dict(parse.parse_qsl(parse.urlparse(get_req_datas).path)))
            else:
                get_req_datas = {}
        except Exception as e:
            get_req_datas = {}
        # 尝试拿到post核载数据
        try:
            post_req_datas = self.rfile.read(int(self.headers['content-length']))
            if isinstance(post_req_datas, bytes):
                post_req_datas = post_req_datas.decode()
                post_req_datas = json.dumps(dict(parse.parse_qsl(parse.urlparse(post_req_datas).path)))
        except Exception as e:
            post_req_datas = {}
        # 如果路径是则去到首页
        if not req_path[0]:
            if gl_rest_path + "index" not in sys.modules:
                try:
                    exec(f"import {gl_rest_path}", globals())
                    exec(f"from {gl_rest_path} import index", globals())
                except Exception as e:
                    res_info = f"模块{gl_rest_path},错误信息：{e}"
                    res = {"static": "1", "info": res_info}
                    self.see_dev_mode(e)
                    return self.showError(res)
            try:
                res_status, res = eval(f"{gl_rest_path}.index.default_index()")
                if res_status == "json":
                    return self.showSuccess(res)
                elif res_status == "text/html":
                    return self.showHtml(res)
            except Exception as e:
                res_info = f"模块{gl_rest_path},错误信息：{e}"
                res = {"static": "1", "info": res_info}
                self.see_dev_mode(e)
                return self.showError(res)
        else:
            if not os.path.exists(os.path.dirname(__file__) + '/../rest/' + req_path[0] + '.py'):
                # print('404', self.path)
                return self.showStatus(404)
        # 加载指定文件夹模块
        if gl_rest_path not in sys.modules:
            try:
                exec(f"import {gl_rest_path}", globals())
            except Exception as e:
                res_info = f"模块{gl_rest_path},错误信息：{e}"
                res = {"static": "1", "info": res_info}
                self.see_dev_mode(e)
                return self.showError(res)
        if f"{gl_rest_path}.{req_path[0]}" not in sys.modules:
            try:
                exec(f"from {gl_rest_path} import {req_path[0]}", globals())
            except Exception as e:
                res_info = f"模块{gl_rest_path}.{req_path[0]},错误信息：{e}"
                res = {"static": "1", "info": res_info}
                self.see_dev_mode(e)
                return self.showError(res)
        # 执行模块方法
        try:
            # 查询映射表
            try:
                url_map = eval(f"{gl_rest_path}.{req_path[0]}.url_maps")
                url_map_dict.update(url_map)
            except Exception as e:
                if str(e) == f"""module '{gl_rest_path}.{req_path[0]}' has no attribute 'url_maps'""":
                    pass
                else:
                    self.see_dev_mode(e)
                    self.showError(f"模块{gl_rest_path}.{req_path[0]} 错误信息：{e}")
            if req_path_str in url_map_dict:
                res_status, res = eval(f"""url_map["{req_path_str}"](url=\"{url}\",path=\"{req_path_str}\",get={get_req_datas},post=\"\",headers={headers})""")
            else:
                res_status, res = eval(f"{gl_rest_path}.{req_path[0]}.{req_path[1]}(url=\"{url}\",path=\"{req_path_str}\",get={get_req_datas},post=\"\",headers={headers})")
        except Exception as e:
            res_info = f"模块{gl_rest_path}.{req_path[0]}.{req_path[1]}错误信息：{e}"
            res = {"static": "1", "info": res_info}
            self.see_dev_mode(e)
            return self.showError(res)
        if res_status == "json":
            self.showSuccess(res)
        elif res_status == "text/html":
            self.showHtml(res)
        elif res_status == "text/plain":
            self.showPlain(res)

    def showHtml(self, res):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(res.encode())

    def showPlain(self, res):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(res.encode())

    def showSuccess(self, res):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        if isinstance(res, dict):
            self.wfile.write(json.dumps(res).encode())
        elif isinstance(res, str):
            self.wfile.write(res.encode())

    def showError(self, res):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        if isinstance(res, dict):
            self.wfile.write(json.dumps(res).encode())
        elif isinstance(res, str):
            self.wfile.write(res.encode())

    def showStatus(self, status):
        self.send_response(status)
        # self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()


if __name__ == '__main__':
    address = ("", 8002)
    # 用ThreadingHttpServer绑定对应的应答类
    server = http.server.ThreadingHTTPServer(address, WebRequestHandler)
    print(f"启动地址{address[0]}:{address[1]}")
    # 监听端口 forever()方法使用select.select()循环监听请求，当接收到请求后调用 当监听到请求时，取出请求对象
    server.serve_forever()
