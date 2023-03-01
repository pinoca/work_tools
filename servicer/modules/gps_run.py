import json
import re
import socket
import time
import requests
from datetime import datetime
from datetime import timedelta
from datetime import timezone
import yaml
from mongoengine import connect, disconnect
from servicer.models.Gps_track_model import Gps_track
from servicer.models.Gps_model import Gps
from concurrent.futures import ThreadPoolExecutor
import logging


class gps(object):
    def __init__(self):
        # 加载yaml配置文件
        with open("config.yaml", "r", encoding="utf-8") as f:
            self.config = yaml.load(f.read(), Loader=yaml.FullLoader)
        # 日志
        logging.basicConfig(
            filename=self.config["mongo_config"]["log_path"],
            format="%(asctime)s-%(name)s-%(levelname)s-%(thread)s-%(message)s-%(funcName)s:%(lineno)d",
            level=logging.DEBUG,
            filemode="w",
        )
        self.thread_run()

    def thread_run(self):
        logging.info("开启GPS监控")
        disconnect(alias="default")
        connect(
            self.config["mongo_config"]["db"],
            host=self.config["mongo_config"]["host"],
            port=self.config["mongo_config"]["port"],
            username=self.config["mongo_config"]["username"],
            password=self.config["mongo_config"]["password"],
            authentication_source=self.config["mongo_config"]["authentication_source"],
        )
        executor = ThreadPoolExecutor(3)
        get_location = executor.submit(self.get_location)
        get_udp_data = executor.submit(self.get_udp_data)
        # 检查线程是否还存活
        while True:
            time.sleep(1)
            if get_location.done():
                get_location = executor.submit(self.get_location)
                logging.error("get_location error")
            if get_udp_data.done():
                get_udp_data = executor.submit(self.get_udp_data)
                logging.error("get_udp_data error")

    # 解析udp数据包
    def get_udp_data(self):
        logging.info("listening port open")
        # 创建socket
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        local_addr = ("", self.config["mongo_config"]["udp_port"])
        udp_socket.bind(local_addr)
        while True:
            recv_data = udp_socket.recvfrom(1024)
            data = recv_data[0].hex()
            if data[4:6] == "80":
                # 拿到解析后的数据
                parse_data = self.Parse_80(data)
                # 用IMEI号，从gps表拿inc_id客户id
                try:
                    gps_id = Gps.objects.filter(gps_id=parse_data["IMEI"])["inc_id"]
                    try:
                        # 判断时间戳是否到达数据库插入条件
                        if (
                                parse_data["Time"]
                                - Gps_track.objects.filter(gps_id=gps_id)
                                .order_by("-id")
                                .first()["created"]
                                > 1800
                        ):
                            Gps_track(
                                gps_id=gps_id,
                                created=parse_data["Time"],
                                lat=parse_data["lat"],
                                addr="",
                                lng=parse_data["lng"],
                                bs=parse_data["bs"],
                                c_code=parse_data["c_code"],
                                data=data,
                                temperature=parse_data["temp"],
                            ).save()
                    except:
                        # 初次判断失败情况为数据库里没有这个设备号，为第一次录入数据
                        Gps_track(
                            gps_id=gps_id,
                            created=parse_data["Time"],
                            lat=parse_data["lat"],
                            addr="",
                            lng=parse_data["lng"],
                            bs=parse_data["bs"],
                            c_code=parse_data["c_code"],
                            data=data,
                            temperature=parse_data["temp"],
                        ).save()
                # 异常没有对应IMEI号的快递
                except:
                    Gps_track(
                        gps_id=0,
                        created=parse_data["Time"],
                        lat=parse_data["lat"],
                        addr="",
                        lng=parse_data["lng"],
                        bs=parse_data["bs"],
                        c_code=parse_data["c_code"],
                        data=data,
                        temperature=parse_data["temp"],
                    ).save()
                # 回复客户端消息
                udp_socket.sendto(bytes.fromhex(parse_data["send_data"]), recv_data[1])
                logging.info("answer 80")
            elif data[4:6].upper() == "D6":
                send_data = self.answer_60(data)
                udp_socket.sendto(bytes.fromhex(send_data), recv_data[1])
                logging.info("answer 60")
            elif data[4:6].upper() == "D8":
                # 默认不应答
                pass

    # 解析80数据包
    def Parse_80(self, data):
        # 时间信息
        Time = int(time.mktime(time.strptime("20" + data[26:38], "%Y%m%d%H%M%S")))
        # 设备号
        IMEI = data[11:26]
        # 34byte位置信息
        location_data = data[26:94]
        location = location_data[12:28]
        # 经度
        longitude = (
                str(int(location[0:3])) + "." + str(int((int(location[3:8]) / 60) * 10))
        )
        # 纬度
        latitude = (
                str(int(location[8:11])) + "." + str(int((int(location[11:]) / 60) * 10))
        )
        # 拓展信息
        expand_data = data[94:-4]
        # 基站
        s_base = expand_data.find(re.search("00.*.*0024", expand_data).group())
        e_base = int(re.search("00.*.*0024", expand_data).group()[2:4], 16)
        base_station_data = expand_data[s_base + 8: s_base + (e_base + 2) * 2]
        # 基站坐标
        base_res = ""
        # 取基站坐标
        for i in range(int(len(base_station_data) / 2)):
            if base_station_data[i * 2 + 1] != "b":
                base_res += base_station_data[i * 2 + 1]
            else:
                base_res += ";"
        # 构建应答数据
        send_data = (
                "2525210005" + data[-4:-2].upper() + data[4:6].upper() + data[26:28].upper()
        )
        send_data = self.get_cheaknum(send_data) + "0D"
        c_code = base_res.split(";")[0]
        try:
            # 尝试拿到取温度值
            temperature_data = re.search("000500d9.{6}", expand_data).group()[8:]
            # 保存一位小数点
            temperature = str(int(temperature_data[-4:]) / 10)
            if temperature_data[1] == "1":
                temperature = "-" + temperature
            return {
                "Time": Time,
                "IMEI": IMEI,
                "lng": longitude,
                "lat": latitude,
                "bs": base_res,
                "c_code": c_code,
                "send_data": send_data,
                "temp": temperature,
            }
        except:
            return {
                "Time": Time,
                "IMEI": IMEI,
                "lng": longitude,
                "lat": latitude,
                "bs": base_res,
                "c_code": c_code,
                "send_data": send_data,
                "temp": 0,
            }

    # 应答60数据包
    def answer_60(self, data):
        SHA_TZ = timezone(timedelta(hours=8), name="Asia/Shanghai", )
        # 协调世界时
        utc_now = datetime.utcnow().replace(tzinfo=timezone.utc)
        # 构建应答数据
        send_data = (
                "2525D70011"
                + data[10:26].upper()
                + utc_now.astimezone(SHA_TZ).strftime("%Y%m%d%H%M%S")[2:]
                + "00"
        )
        send_data = self.get_cheaknum(send_data) + "0D"
        return send_data

    # 得到校验码
    def get_cheaknum(self, data):
        # 构建转义
        tran = {
            "0": "0000",
            "1": "0001",
            "2": "0010",
            "3": "0011",
            "4": "0100",
            "5": "0101",
            "6": "0110",
            "7": "0111",
            "8": "1000",
            "9": "1001",
            "A": "1010",
            "B": "1011",
            "C": "1100",
            "D": "1101",
            "E": "1110",
            "F": "1111",
        }
        aa = data.upper()
        bindata = ""
        # 转二进制
        for i in range(len(aa)):
            bindata += tran[aa[i]]
        d = bindata[0:8]
        # 验证计算
        for i in range(1, int(len(data) / 2)):
            d2 = bindata[i * 8: i * 8 + 8]
            temp = ""
            for j in range(8):
                temp += str(int(d[j]) ^ int(d2[j]))
            d = temp
        d = str(d)
        # 高位补0
        while len(d) != 8:
            d = "0" + d
        s1 = ""
        s2 = ""
        # 二进制转16
        for k, v in tran.items():
            if d[0:4] == v:
                s1 = k
            elif d[4:] == v:
                s2 = k
        return data + s1 + s2

    # 拿到真实地址
    def get_location(self):
        logging.info("Database location information update enabled")
        while True:
            time.sleep(2)
            try:
                # 从数据库取出要查询的数据
                info = Gps_track.objects.filter(addr="")
                for i in range(0, len(info)):
                    # 坐标信息INSUFFICIENT_ABROAD_PRIVILEGES
                    try:
                        long_la = info[i]["lat"] + "," + info[i]["lng"]
                        res = requests.request(
                            "GET",
                            url="https://restapi.amap.com/v3/geocode/regeo?output=json&location="
                                + long_la
                                + "&key=", # 地址查询方法自查
                        )
                        location_info = json.loads(res.text)
                        location_dict = location_info["regeocode"]["addressComponent"]
                        # 尝试拿准确地址
                        try:
                            location = (
                                    location_dict["province"]
                                    + location_dict["city"]
                                    + location_dict["district"]
                                    + location_dict["streetNumber"]["street"]
                                    + location_dict["streetNumber"]["number"]
                            )
                            info[i].update(addr=location)
                            logging.info("update completed")
                        except:
                            location = location_dict["province"] + location_dict["city"]
                            info[i].update(addr=location)
                            logging.info("province & city update completed")
                    except Exception as e:
                        logging.error("updata fail because:", e)
            except:
                pass


if __name__ == "__main__":
    GPSobj = gps()
