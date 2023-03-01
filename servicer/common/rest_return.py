def success(data=None):
    if data is None:
        data = {}
    return "json", data


def success_jsonp(callback, data=None, info="操作成功"):
    html_content = f"{str(callback)}({str(data)})"
    return "text/plain", html_content


def error(data=None):
    if data is None:
        data = {}
    return "json", data



def html(html_content):
    return "text/html", html_content


def plain(plain_content):
    return "text/plain", plain_content


