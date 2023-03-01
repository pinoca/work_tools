import json
import sys
import uuid
from PyPDF2 import PdfWriter, PdfReader, PdfMerger
from pdf2image import convert_from_path
from PIL import Image
import base64
import re
import xml.dom.minidom as xmldom
import os
import zipfile
import shutil
import cv2
import pyzbar.pyzbar as pyzbar

"""
    pdf2image需要下载插件，用于pdf转图片
"""


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


def current_file_path():
    """
    返回当前路径
    :return: str
    """
    path = sys.path[0]
    if os.path.isdir(path):
        return path
    elif os.path.isfile(path):
        return os.path.dirname(path)


def format_path(path: str):
    """
    格式化路径字符串，由于python字符串读取规则做的防路径错误设计
    path：需要格式化的路径
    """
    res = path.replace("\\", "/").replace("//", "/").replace("\\\\", "/").replace("////", "/")
    return res


def get_filename_and_extension(filename):
    """
    文件名和拓展名
    :param filename: 文件路径
    :return:(文件名,文件拓展名) -> tuple
    """
    (filepath, tempfilename) = os.path.split(filename)
    (shotname, extension) = os.path.splitext(tempfilename)
    return shotname, extension


def pdf_page_apart(f_path, option_to='pdf', dpi=203, identify=False, step=1, rotate_angle=0):
    """
    用于分离pdf linux系统需要安装poppler-utils用于转图片
    :param dpi:每英寸的像素点数
    :param option_to: 分离后的保存形式
    :param f_path: 需要分离的pdf文件路径
    :param step: 分离步长
    :param identify: 是否识别条形码
    :param rotate_angle pdf旋转度数
    :return: [（文件名，字节流） * n]
    """
    # 实例化
    p_reader = PdfReader(f_path)
    w_writer = PdfWriter()
    identify_res = {}
    # 遍历pdf页分割
    for index in range(p_reader.numPages):
        # 旋转
        if rotate_angle:
            page = p_reader.getPage(index).rotate(rotate_angle)
        else:
            page = p_reader.getPage(index)
        # 生成pdf
        w_writer.add_page(page)
        w_writer.write(format_path(os.path.dirname(f_path) + f"\\page_{index}.pdf"))
        # 生成png图片
        png_images = convert_from_path(format_path(os.path.dirname(f_path) + f"\\page_{index}.pdf"), dpi=dpi)
        for image in png_images:
            # 保存图片
            image.save(format_path(os.path.dirname(f_path) + f"\\page_{index}.png"), 'PNG')
            if identify:
                identify_res[f"page_{index}"] = identify_barcode(format_path(os.path.dirname(f_path) + f"\\page_{index}.png"))
        w_writer = PdfWriter()
    # 遍历生成好的文件,生成返回数据
    os.remove(f_path)
    res_dict = {}
    label_dict = {}
    res_list = []
    files = os.listdir(os.path.dirname(f_path))
    for name in files:
        if option_to == "pdf" and get_filename_and_extension(name)[1] != ".pdf":
            continue
        if option_to == "png" and get_filename_and_extension(name)[1] != ".png":
            continue
        with open(format_path(os.path.join(f_path.rsplit("/", 1)[0], name)), "rb") as f:
            res_content = f.read()
            if identify:
                label_dict[name] = str(base64.b64encode(res_content))[2:-1]
            else:
                res_list.append(name)
                res_list.append(str(base64.b64encode(res_content))[2:-1])
    if identify_res:
        res_dict["label"] = label_dict
        res_dict["numbers"] = identify_res
        return res_dict
    else:
        return res_list


def identify_barcode(img_path):
    """
    识别图片里的条形码
    :param img_path: 图片路径
    :return: 返回识别结果->list
    """
    img_data = cv2.imread(format_path(img_path))
    gray = cv2.cvtColor(img_data, cv2.COLOR_BGR2GRAY)
    barcodes = pyzbar.decode(gray)
    res_arr = []
    for code in barcodes:
        res_arr.append(code.data.decode("utf-8"))
    return res_arr


def pdf_cropping(f_path, p_x, p_y, p_w, p_h):
    """
    输入坐标，宽高对pdf进行裁剪
    :param f_path: dpf路径
    :param p_x: 坐标x 要截图的右上点，发送过来的数据默认为右上为坐标原点
    :param p_y: 坐标y
    :param p_w: x轴偏移量
    :param p_h: y轴偏移量
    :return: 返回新pdf保存路径
    """
    reader = PdfReader(f_path)
    writer = PdfWriter()
    page = reader.getPage(0)
    # 库左下为坐标原点
    page.mediabox.upper_left = (p_x, page.mediabox.top - p_y)
    page.mediabox.upper_right = (p_x + p_w, page.mediabox.top - p_y)
    page.mediabox.lower_left = (p_x, page.mediabox.top - (p_y + p_h))
    page.mediabox.lower_right = (p_x + p_w, page.mediabox.top - (p_y + p_h))
    writer.add_page(page)
    # 写入到新文件
    writer.write(format_path(os.path.dirname(f_path) + "\\new.pdf"))
    return format_path(os.path.dirname(f_path) + "\\new.pdf")


def img_vconcat(img_list, height=0):
    """
    图片拼接
    :param img_list: 图片拼接列表
    :param height: 增加的高度
    :return: 图片路径
    """
    exec_str = "cv2.vconcat(["
    for img_path in img_list:
        exec_str += f"""cv2.imread(r"{format_path(img_path)}"),"""
    exec_str = exec_str[:-1] + "])"
    img = eval(exec_str)
    res_path = format_path(os.path.dirname(img_list[0]) + "/2222.png")
    cv2.imwrite(res_path, img)
    return res_path


def img2pdf(img_path: str):
    """
    图片转pdf
    :param img_path:
    :return:pdf路径
    """
    im1 = Image.open(format_path(img_path))
    base_name = os.path.basename(img_path).split(".")[0] + ".pdf"
    res_path = format_path(os.path.dirname(img_path) + "\\" + base_name)
    im1.save(res_path, "PDF", resolution=200.0)
    return res_path


def list_str_to_list(list_str):
    """
    处理过来就是加密的list
    :param list_s:
    :return:
    """
    list_s = list_str[3:-2]
    list_s_l = list_s.split("},")
    res_list = []
    list_s_l[-1] = list_s_l[-1][:-1]
    for i in list_s_l:
        res_list.append(json.loads(i + "}"))
    return res_list


class pdf_tool:
    def do_pdfseparate(self, data):
        """
        分割pdf
        :param data: 请求体核载
        :return: 操作状态，[文件名,b64加密字节流 *n] ->list
        """
        # 请求体中核载的pdf字节流
        content = base64_decode(data['fileContent'])
        # 构建存储路径
        tmp_path = current_file_path() + "/tmp/"
        dir_name = str(uuid.uuid1())
        pdf_save_path = format_path(tmp_path + "/" + dir_name + "/pdf.pdf")
        # 临时存储成pdf文件供后续操作
        os.makedirs(format_path(tmp_path + "/" + dir_name), exist_ok=True)
        with open(pdf_save_path, "wb") as f:
            f.write(content)
        # 分离pdf
        option_to = data.get("option_to", "pdf")
        identify = True if data.get("identify", False) else False
        rotate_angle = int(data.get("rotate_angle", 0))
        res = pdf_page_apart(f_path=pdf_save_path, option_to=option_to, identify=identify, rotate_angle=rotate_angle)
        # 递归删除临时文件和文件夹
        shutil.rmtree(format_path(tmp_path + "/" + dir_name))
        return 1, res

    def do_pdfsplit(self, data):
        self.do_pdfseparate(data)

    def do_pdftocairo(self, data):
        """
        裁切PDF
        :param data: 请求体核载
        :return: 操作状态，b64加密的bytes_list
        """
        # 请求体中核载的pdf字节流
        content = base64_decode(data['fileContent'])
        # 构建存储路径
        tmp_path = current_file_path() + "/tmp/"
        dir_name = str(uuid.uuid1())
        pdf_save_path = format_path(tmp_path + "/" + dir_name + "/pdf.pdf")
        # 临时存储成pdf文件供后续操作
        os.makedirs(format_path(tmp_path + "/" + dir_name), exist_ok=True)
        with open(pdf_save_path, "wb") as f:
            f.write(content)
        if isinstance(data["opt"], dict):
            # 拿出请求体中要裁剪的范围
            p_x = data["opt"].get("x", data["opt"].get("-x", data["opt"].get("X", data["opt"].get("-X", ""))))
            p_y = data["opt"].get("y", data["opt"].get("-y", data["opt"].get("Y", data["opt"].get("-Y", ""))))
            p_w = data["opt"].get("w", data["opt"].get("-w", data["opt"].get("W", data["opt"].get("-W", ""))))
            p_h = data["opt"].get("h", data["opt"].get("-h", data["opt"].get("H", data["opt"].get("-H", ""))))
        else:
            data["opt"] = dict(data["opt"])
            p_x = data["opt"].get("x", data["opt"].get("-x", data["opt"].get("X", data["opt"].get("-X", ""))))
            p_y = data["opt"].get("y", data["opt"].get("-y", data["opt"].get("Y", data["opt"].get("-Y", ""))))
            p_w = data["opt"].get("w", data["opt"].get("-w", data["opt"].get("W", data["opt"].get("-W", ""))))
            p_h = data["opt"].get("h", data["opt"].get("-h", data["opt"].get("H", data["opt"].get("-H", ""))))
        if not (p_x != "" and p_y != "" and p_w != "" and p_h != ""):
            shutil.rmtree(format_path(tmp_path + "/" + dir_name))
            return 0, "缺少opt参数或者opt内参数缺失"
        # 调用裁剪函数
        new_path = pdf_cropping(pdf_save_path, int(p_x), int(p_y), int(p_w), int(p_h))
        # 拿到裁剪后的pdf后进行加密后返回
        with open(new_path, "rb") as f:
            res = base64_encode(f.read())
        res_list = [str(res)]
        # 递归删除临时文件和文件夹
        shutil.rmtree(format_path(tmp_path + "/" + dir_name))
        return 1, res_list

    def do_pdfunite(self, data):
        """
        合并pdf
        :param data:请求体核载
        :return:操作状态，b64加密的str
        """
        # 构建存储路径
        tmp_path = current_file_path() + "/tmp/"
        dir_name = str(uuid.uuid1())
        # 临时存储成pdf文件供后续操作
        os.makedirs(format_path(tmp_path + "/" + dir_name), exist_ok=True)
        # 初始化合并对象 按默认发送过来的顺序合并
        merger = PdfMerger()
        # 请求体中核载的pdf字节流
        if data["files"][0] == "{":
            #   字典格式
            files = json.loads(base64_decode(data["files"]))
            # 遍历核载发送过来的文件字节流
            for k, v in files.items():
                pdf_save_path = format_path(tmp_path + "/" + dir_name + f"""/pdf_{k}.{v["type"]}""")
                with open(pdf_save_path, "wb") as f:
                    f.write(base64_decode(v["content"]))
                merger.append(format_path(tmp_path + "/" + dir_name + f"""/pdf_{k}.{v["type"]}"""))
        else:
            # 字符串类型
            if isinstance(data["files"], str):
                file_info = str(base64_decode(data["files"]))
                data["files"] = list_str_to_list(file_info)
            # list类型
            if isinstance(data["files"], list):
                for i, v in enumerate(data["files"]):
                    pdf_save_path = format_path(tmp_path + "/" + dir_name + f"""/pdf_{i}.{v["type"]}""")
                    with open(pdf_save_path, "wb") as f:
                        f.write(base64_decode(v["content"]))
                    if v["type"] != "pdf":
                        img_save_path = img2pdf(pdf_save_path)
                        merger.append(img_save_path)
                    else:
                        merger.append(pdf_save_path)
        merger.write(format_path(tmp_path + "/" + dir_name + "pdf_done.pdf"))
        merger.close()
        with open(format_path(tmp_path + "/" + dir_name + "pdf_done.pdf"), "rb") as f:
            res_content = base64_encode(f.read())
        shutil.rmtree(format_path(tmp_path + "/" + dir_name))
        return 1, str(res_content)

    def do_pdfappend(self, data):
        """
        拼接dpf
        :param data:
        :return: 返回拼接好b64加密转字符串的字节流->str
        """
        # 在文件下面增加指定高度和内容
        # 构建存储路径
        tmp_path = current_file_path() + "/tmp/"
        dir_name = str(uuid.uuid1())
        # 临时存储成pdf文件供后续操作
        os.makedirs(format_path(tmp_path + "/" + dir_name), exist_ok=True)
        img_name_list = []
        # 请求体中核载的pdf字节流
        if data['files'][0] == "{":
            # 字典套字典形式
            files = json.loads(base64_decode(data['files']))
            # 遍历核载发送过来的文件字节流
            for k, v in files.items():
                c_save_path = format_path(tmp_path + "/" + dir_name + f"""/pdf_{k}.{v["type"]}""")
                with open(c_save_path, "wb") as f:
                    f.write(base64_decode(v["content"]))
                # 不是图片就转成图片进行pdf转图片
                if v['type'] != "png":
                    png_images = convert_from_path(format_path(c_save_path), dpi=203)
                    for image in png_images:
                        # 保存图片
                        image.save(format_path(tmp_path + "/" + dir_name + f"""/pdf_{k}.png"""), 'PNG')
                img_name_list.append(format_path(tmp_path + "/" + dir_name + f"""/pdf_{k}.png"""))
        else:
            # 列表
            for i, v in enumerate(data['files']):
                c_save_path = format_path(tmp_path + "/" + dir_name + f"""/pdf_{i}.{v["type"]}""")
                with open(c_save_path, "wb") as f:
                    f.write(base64_decode(v["content"]))
                if v['type'] != "png":
                    png_images = convert_from_path(format_path(c_save_path), dpi=203)
                    for image in png_images:
                        # 保存图片
                        image.save(format_path(tmp_path + "/" + dir_name + f"""/pdf_{i}.png"""), 'PNG')
                # 保存图片路径
                img_name_list.append(format_path(tmp_path + "/" + dir_name + f"""/pdf_{i}.png"""))
        # 拿到图片合成后的路径
        res_png_path = img_vconcat(img_name_list)
        if data.get("option_to", "") == "png":
            with open(res_png_path, 'rb') as f:
                content = base64_encode(f.read())
            shutil.rmtree(format_path(tmp_path + "/" + dir_name))
            return 1, content
        # 图片转pdf
        else:
            dpf_path = img2pdf(res_png_path)
            with open(dpf_path, 'rb') as f:
                content = base64_encode(f.read())
            shutil.rmtree(format_path(tmp_path + "/" + dir_name))
            return 1, content

    def do_htmltox(self, data):
        """
        html转pdf
        :param data:
        :return:状态码 list
        """
        data.update({"option_dpi": "230"})
        # 构建存储路径
        tmp_path = current_file_path() + "/modules/tmp/"
        dir_name = str(uuid.uuid1())
        # 存储路径
        pdf_save_path = format_path(tmp_path + "/" + dir_name + "/page.pdf")
        os.makedirs(format_path(tmp_path + "/" + dir_name), exist_ok=True)
        # 工具路径
        wkhtmltopdfPath = tmp_path + "/wkhtmltox/bin/wkhtmltopdf"
        # 请求体中核载的pdf字节流
        content = str(base64_decode(data['fileContent']))[2:-1]
        # html模板
        with open(format_path((tmp_path + "/htmltox_tpl.html")), "r") as f:
            tpl_content = f.read()
            content = tpl_content.replace("{content}", content)
        # 保存构造的html
        with open(format_path(tmp_path + "/" + dir_name + "/page.html"), "w+") as f:
            f.write(content)
        # 构造使用工具命令
        html_file = format_path(tmp_path + "/" + dir_name + "/page.html")
        os_cmd = wkhtmltopdfPath + ' --page-width ' + data['option_page_width'] + ' --page-height ' + data['option_page_height'] + ' --margin-top ' + data['option_margin_top'] + ' --margin-bottom ' + \
                 data['option_margin_bottom'] + ' --margin-left ' + data['option_margin_left'] + ' --margin-right ' + data['option_margin_right'] + ' ' + html_file + " " + pdf_save_path
        os.system(os_cmd)
        # 返回了列表
        res_arr = []
        if os.path.exists(pdf_save_path):
            # 判断是否分离pdf
            if data["option_multi"] == "1":
                # 分离pdf
                dpi = data.get("option_dpi", 203)
                option_to = data.get("option_to", "pdf")
                identify = True if data.get("identify", False) else False
                rotate_angle = int(data.get("rotate_angle", 0))
                res_arr = pdf_page_apart(f_path=pdf_save_path, option_to=option_to, identify=identify, rotate_angle=rotate_angle, dpi=dpi)
            else:
                with open(pdf_save_path, "rb") as f:
                    res_content = f.read()
                    res_arr.append(str(base64.b64encode(res_content))[2:-1])
        # 递归删除临时文件和文件夹
        shutil.rmtree(format_path(tmp_path + "/" + dir_name))
        return 1, res_arr

    def do_excel2csv(self, content, ext, app_code="", get_img=False):
        """
        excel 转 csv 使用libreoffice
        :param app_code: app代码
        :param content: 核载内容
        :param ext: excel的格式
        :param get_img: 拿excel里图片信息
        :return:状态码 str
        """
        content = base64_decode(content)
        # 保存路径
        if app_code:
            dir_name = str(uuid.uuid1()) + "-" + app_code
        else:
            dir_name = str(uuid.uuid1())
        tmp_path = current_file_path() + "/tmp/"
        os.makedirs(format_path(tmp_path + "/" + dir_name), exist_ok=True)
        # excel保存路径
        tmpExcelFile = format_path(tmp_path + "/" + dir_name + f"/temp.{ext}")
        with open(tmpExcelFile, "wb") as f:
            f.write(content)
        # 要保存的csv文件路径
        csvFile = format_path(tmp_path + "/" + dir_name + f"/temp.csv")
        os_cmd = f"""libreoffice7.3 --headless --convert-to csv {tmpExcelFile} --outdir {format_path(tmp_path + "/" + dir_name)}"""
        if os.path.exists(tmpExcelFile):
            os.system(os_cmd)
        else:
            return 0, 0
        if os.path.exists(csvFile):
            with open(csvFile, "rb") as f:
                content = base64_encode(f.read())
            if get_img:
                # 只转xlsx
                if ext == "xls":
                    xlsx_tmpExcelFile = xls2xlsx(format_path(tmp_path + "/" + dir_name + f"/temp.xls"), format_path(tmp_path + "/" + dir_name + f"/temp.xlsx"))[1]
                else:
                    xlsx_tmpExcelFile = tmpExcelFile
                if os.path.exists(format_path(xlsx_tmpExcelFile)):
                    # 调用拿图片函数
                    res_list = get_img_info(xlsx_tmpExcelFile)
                    res_dict = {}
                    res_dict["csv"] = content
                    res_dict["img"] = res_list
                    shutil.rmtree(format_path(tmp_path + "/" + dir_name))
                    return 1, res_dict
                else:
                    shutil.rmtree(format_path(tmp_path + "/" + dir_name))
                    return 0, "生成xlsx表格错误"
            else:
                shutil.rmtree(format_path(tmp_path + "/" + dir_name))
                return 1, content
        else:
            shutil.rmtree(format_path(tmp_path + "/" + dir_name))
            return 0, content

    def xls2xlsx(self, content, app_code, name=""):
        """
        xls 转 xlsx格式
        :param content: file内容
        :param name: 文件名
        :param app_code: app代码
        :return:
        """
        content = base64_decode(content)
        # 保存路径
        if app_code:
            dir_name = str(uuid.uuid1()) + "-" + app_code
        else:
            dir_name = str(uuid.uuid1())
        tmp_path = current_file_path() + "/tmp/"
        # xls保存路径
        tmp_xls_file = format_path(tmp_path + "/" + dir_name + f"/temp.xls")
        os.makedirs(format_path(tmp_path + "/" + dir_name), exist_ok=True)
        with open(tmp_xls_file, "wb") as f:
            f.write(content)
        # 要保存的xlsx文件路径
        xlsx_file = format_path(tmp_path + "/" + dir_name + f"/temp.xlsx")
        if os.path.exists(tmp_xls_file):
            success, xlsx_file = xls2xlsx(tmp_xls_file, xlsx_file)
        else:
            shutil.rmtree(format_path(tmp_path + "/" + dir_name))
            return 0, 0
        if success:
            if os.path.exists(xlsx_file):
                with open(xlsx_file, "rb") as f:
                    content = base64_encode(f.read())
                    shutil.rmtree(format_path(tmp_path + "/" + dir_name))
                    return 1, content
            else:
                shutil.rmtree(format_path(tmp_path + "/" + dir_name))
                return 0, content
        else:
            shutil.rmtree(format_path(tmp_path + "/" + dir_name))
            return 0, 0

    def do_excel2csv_pd(self, content, ext, app_code):
        self.do_excel2csv(content, ext, app_code)

    def get_xlsx_img_info(self, content, app_code=""):
        """
        拿到xlsx里的图片信息
        :param content:
        :param app_code:
        :return:
        """
        content = base64_decode(content)
        # 保存路径
        if app_code:
            dir_name = str(uuid.uuid1()) + "-" + app_code
        else:
            dir_name = str(uuid.uuid1())
        tmp_path = current_file_path() + "/tmp/"
        # xls保存路径
        tmp_xls_file = format_path(tmp_path + "/" + dir_name + f"/temp.xlsx")
        os.makedirs(format_path(tmp_path + "/" + dir_name), exist_ok=True)
        with open(tmp_xls_file, "wb") as f:
            f.write(content)
        # 拿xlsx内图片位置信息 返回一个列表，带有图片索引位置信息[行 ， 列， 图片路径， base64加密的字符串]
        res_list = get_img_info(format_path(tmp_xls_file))
        shutil.rmtree(format_path(tmp_path + "/" + dir_name))
        return 1, res_list


def xls2xlsx(xls_path, xlsx_path):
    """
    xls 转 xlsx格式 liberoffice
    :param xls_path:
    :param xlsx_path:
    :return:判断状态+路径
    """
    os_cmd = f"libreoffice7.3 --headless --convert-to xlsx {xls_path} --outdir {format_path(os.path.dirname(xlsx_path))}"
    os.system(os_cmd)
    if os.path.exists(format_path(xlsx_path)):
        return True, format_path(xlsx_path)
    else:
        return False, 0


def isfile_exist(file_path):
    """
    判断文件是否存在
    :param file_path: 文件路径
    :return: 布尔类型
    """
    if not os.path.isfile(file_path):
        print("It's not a file or no such file exist ! %s" % file_path)
        return False
    else:
        return True


def copy_change_file_name(file_path, new_type='.zip') -> str:
    """
    复制并修改指定目录下的文件类型名，将excel后缀名修改为.zip
    :param file_path: 要复制的文件目录
    :param new_type: 复制后的类型
    :return: 返回新的文件路径，压缩包
    """
    file_path = format_path(file_path)
    if not isfile_exist(file_path):
        return ""

    extend = os.path.splitext(file_path)[1]  # 获取文件拓展名
    if extend != '.xlsx' and extend != '.xls':
        print("It's not a excel file! %s" % file_path)
        return ""

    file_name = os.path.basename(file_path)  # 获取文件名
    new_name = str(file_name.split('.')[0]) + new_type  # 新的文件名，命名为：xxx.zip

    dir_path = os.path.dirname(file_path)  # 获取文件所在目录
    new_path = format_path(os.path.join(dir_path, new_name))  # 新的文件路径
    if os.path.exists(new_path):
        os.remove(new_path)
    shutil.copyfile(file_path, new_path)
    return new_path


def unzip_file(zipfile_path) -> bool:
    """
    解压文件
    :param zipfile_path: 要解压的zip文件路径
    :return: 返回解压状态
    """
    if not isfile_exist(zipfile_path):
        return False
    if os.path.splitext(zipfile_path)[1] != '.zip':
        print("It's not a zip file! %s" % zipfile_path)
        return False
    file_zip = zipfile.ZipFile(zipfile_path, 'r')
    file_name = os.path.basename(zipfile_path)  # 获取文件名
    zipdir = os.path.join(os.path.dirname(zipfile_path), str(file_name.split('.')[0]))  # 获取文件所在目录
    for files in file_zip.namelist():
        # print([os.path.join(zipfile_path, zipdir)])
        file_zip.extract(files, zipdir)  # 解压到指定文件目录
        # file_zip.extract(files)  # 解压到指定文件目录
    file_zip.close()
    return True


def read_img(excel_file_path):
    """
    读取解压后的文件夹，打印图片路径
    :param excel_file_path: 解压后的excel文件路径
    :return:
    """
    excel_file_path = format_path(excel_file_path)
    zipfile_path = str(os.path.splitext(excel_file_path)[0])
    img_dict = dict()
    # 获取文件所在目录
    dir_path = os.path.dirname(zipfile_path)
    # 获取文件名
    file_name = os.path.basename(zipfile_path)
    # excel变成压缩包后，再解压，图片在media目录
    pic_dir = 'xl' + os.sep + 'media'
    pic_path = format_path(os.path.join(dir_path, str(file_name.split('.')[0]), pic_dir))
    file_list = os.listdir(pic_path)
    file_list.sort(key=lambda x: int(str(x).replace('image', '').split('.')[0]))
    for file in file_list:
        filepath = format_path(os.path.join(pic_path, file))
        img_index = int(re.findall(r'image(\d+)\.', filepath)[0])
        img_base64 = get_img_base64(img_path=filepath)
        img_dict[str(img_index)] = dict(img_index=img_index, img_path=filepath, img_base64=img_base64)
    return img_dict


def get_img_base64(img_path):
    """
    获取img_base64
    :param img_path:
    :return: base64加密过的字节流字符串
    """
    if not isfile_exist(img_path):
        return ""
    with open(img_path, 'rb') as f:
        base64_data = base64.b64encode(f.read())
        res_d = base64_encode(base64_data)
        # s = 'data:image/jpeg;base64,%s' % base64_data.decode()
        return res_d


def get_img_pos_info(excel_file_path, img_dict):
    """
    解析xml 文件，获取图片在excel表格中的索引位置信息
    :param excel_file_path:excel的压缩包
    :param img_dict:图片信息字典
    :return: 图片索引位置信息[行 ， 列， 图片路径， base64加密的字符串]
    """
    zip_file_path = str(os.path.splitext(excel_file_path)[0])
    os.path.dirname(zip_file_path)
    dir_path = os.path.dirname(zip_file_path)  # 获取文件所在目录
    file_name = os.path.basename(zip_file_path)  # 获取文件名
    xml_dir = 'xl' + os.sep + 'drawings' + os.sep + 'drawing1.xml'
    xml_path = format_path(os.path.join(dir_path, str(file_name.split('.')[0]), xml_dir))
    image_info_list = parse_xml(xml_path, img_dict)  # 解析xml 文件， 返回图片索引位置信息
    return image_info_list


def get_img_info(excel_file_path) -> list:
    """
    重命名解压获取图片位置，及图片表格索引信息
    :param excel_file_path:要处理的xlsx表格
    :return:返回一个列表，带有图片索引位置信息[行 ， 列， 图片路径， base64加密的字符串]
    """
    zip_file_path = copy_change_file_name(excel_file_path)
    if zip_file_path != "":
        if unzip_file(zip_file_path):
            img_dict = read_img(excel_file_path)  # 获取图片，返回字典，图片 img_index， img_index， img_path， img_base6
            image_info_list = get_img_pos_info(zip_file_path, img_dict)
            shutil.rmtree(format_path(os.path.dirname(excel_file_path) + "/" + os.path.basename(excel_file_path).split(".")[0]))
            os.remove(format_path(os.path.dirname(excel_file_path) + "/" + os.path.basename(excel_file_path).split(".")[0] + ".zip"))
            return image_info_list
    shutil.rmtree(format_path(os.path.dirname(excel_file_path) + "/" + os.path.basename(excel_file_path).split(".")[0]))
    os.remove(format_path(os.path.dirname(excel_file_path) + "/" + os.path.basename(excel_file_path).split(".")[0] + ".zip"))
    return []


def parse_xml(file_name, img_dict):
    """
    解析xml文件并获取对应图片位置
    :param file_name: xml文件路径
    :param img_dict: 图片信息字典
    :return:返回一个列表，带有图片索引位置信息[行 ， 列， 图片路径， base64加密的字符串]
    """
    # 得到文档对象
    image_info = []
    dom_obj = xmldom.parse(format_path(file_name))
    # 得到元素对象
    element = dom_obj.documentElement

    def _f(subElementObj):
        for anchor in subElementObj:
            xdr_from = anchor.getElementsByTagName('xdr:from')[0]
            # 获取行列
            col = xdr_from.childNodes[0].firstChild.data  # 获取标签间的数据
            row = xdr_from.childNodes[2].firstChild.data
            # print(anchor.getElementsByTagName('xdr:pic'))
            # print(anchor.getElementsByTagName('xdr:pic')[0])
            # 拿到元素对象名字
            try:
                embed = anchor.getElementsByTagName('xdr:pic')[0].getElementsByTagName('xdr:blipFill')[0].getElementsByTagName('a:blip')[0].getAttribute('r:embed')  # 获取属性
            except Exception as e:
                print(e)
                embed = ""
            # print(embed)`
            if "embed" in locals():
                # 返回的数据为  行 ， 列， 图片路径， base64加密的字符串
                image_info.append([int(row), int(col), img_dict.get(str(embed.replace("rId", "")), {}).get("img_base64")])

    sub_twoCellAnchor = element.getElementsByTagName("xdr:twoCellAnchor")
    # sub_oneCellAnchor = element.getElementsByTagName("xdr:oneCellAnchor")
    _f(sub_twoCellAnchor)
    return image_info


if __name__ == '__main__':
    # zip_path = format_path(r"D:\Work_Space\mws\tools\tmp\1212.zip")
    # if os.path.exists(zip_path):
    #     os.remove(zip_path)
    # zip = zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED)
    # zip.write(format_path(r"D:\Work_Space\mws\tools\tmp\1212.xlsx"))
    # zip.close()
    res = get_img_info(format_path(r"D:\Work_Space\mws\tools\p1\test2.xls"))
    print(res)
    # pass
