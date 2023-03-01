import random
import threading
import time
import mongoengine
import yaml
import pymongo
import os
from servicer.models.Rest_token_model import Rest_token
from servicer.config import token_config

# 文件路径
path = os.path.join(os.path.dirname(__file__))

sys_params = token_config


class DatabaseOptions:
    def __init__(self):
        # 加载yaml配置文件
        with open(path[:-17] + "config.yaml", "r", encoding="utf-8") as f:
            token_config.YAML_CONFIG = yaml.load(f.read(), Loader=yaml.FullLoader)
        # # 链接数据库 mongodb://账号:密码@服务器IP:27017"
        if token_config.MONGODB_CONFIG_TYPE == "mongo_config":
            self.pymon_connect = pymongo.MongoClient(
                "mongodb://localhost:27017")
        else:
            self.pymon_connect = pymongo.MongoClient(
                "mongodb://" + token_config.YAML_CONFIG[token_config.MONGODB_CONFIG_TYPE]["username"] + ":" +
                token_config.YAML_CONFIG[token_config.MONGODB_CONFIG_TYPE][
                    "password"] + "@" + token_config.YAML_CONFIG[token_config.MONGODB_CONFIG_TYPE]["host"] + ":" + str(
                    token_config.YAML_CONFIG[token_config.MONGODB_CONFIG_TYPE][
                        "port"]) + "/")
        # mongoengine orm框架操作
        mongoengine.disconnect(alias="default")
        mongoengine.connect(
            token_config.YAML_CONFIG[token_config.MONGODB_CONFIG_TYPE]["token_db"],
            host=token_config.YAML_CONFIG[token_config.MONGODB_CONFIG_TYPE]["host"],
            port=token_config.YAML_CONFIG[token_config.MONGODB_CONFIG_TYPE]["port"],
            username=token_config.YAML_CONFIG[token_config.MONGODB_CONFIG_TYPE]["username"],
            password=token_config.YAML_CONFIG[token_config.MONGODB_CONFIG_TYPE]["password"],
            authentication_source=token_config.YAML_CONFIG[token_config.MONGODB_CONFIG_TYPE]["authentication_source"],
        )
        self.token_data_list = []
        print("数据库操作对象初始化")

    def db_get_token_date(self):
        """
        从数据库中拿到token数据
        """
        while True:
            # 判断是否进行特定token导入原始的数据库数据
            if not token_config.YAML_CONFIG["mongo_config"]["token_type_list"]:
                for token_table in token_config.YAML_CONFIG[token_config.MONGODB_CONFIG_TYPE]["token_collection_list"]:
                    collection = self.pymon_connect[token_config.YAML_CONFIG[token_config.MONGODB_CONFIG_TYPE]["token_db"]][
                        token_table]
                    # 去数据库拿到数据，条件为数据库更新时间大于本地最后更新时间
                    token_info = collection.find({"updated": {"$gt": token_config.LAST_UPDATA_TIME}})
                    self.token_data_list = [info for info in token_info]
                #  不为空则进入更新
                if self.token_data_list:
                    # 构建并发控制器的token字典，传入并发控制器对象
                    self.build_token_concurrency_dict()
            else:
                for token_table in token_config.YAML_CONFIG[token_config.MONGODB_CONFIG_TYPE]["token_collection_list"]:
                    collection = self.pymon_connect[token_config.YAML_CONFIG[token_config.MONGODB_CONFIG_TYPE]["token_db"]][
                        token_table]
                    # 去数据库拿到数据，条件为数据库更新时间大于本地最后更新时间，token类型为yaml文件设置的token类型
                    for t_type in token_config.YAML_CONFIG["mongo_config"]["token_type_list"]:
                        token_info = collection.find({"type": t_type,
                                                      "updated": {"$gt": token_config.LAST_UPDATA_TIME}
                                                      })
                        self.token_data_list = [info for info in token_info]
                #  不为空则进入更新
                if self.token_data_list:
                    # 构建并发控制器的token字典，传入并发控制器对象
                    self.build_token_concurrency_dict()
            print("check done once")
            print(len(token_config.CONTROL_ROT_CLS.token_concurrency_dict))
            time.sleep(token_config.DB_VIST_TIME)

    @staticmethod
    def test():
        for i in range(5000):
            b = str(i)
            Rest_token(type="test", token="test" + b, ratelimit=random.choice([i for i in range(20)]),
                       ratelimit_mode=random.choice([0, 1]), updated=int(time.time()), lock=0,
                       timeout=random.choice([1, 2, 3])).save()

    @staticmethod
    def test_type():
        while True:
            time.sleep(5)
            with open(path[:-17] + "config.yaml", "r", encoding="utf-8") as f:
                token_config.YAML_CONFIG = yaml.load(f.read(), Loader=yaml.FullLoader)
            print(token_config.YAML_CONFIG["mongo_config"]["token_type_list"])

    def build_token_concurrency_dict(self):
        print("in build_token_concurrency_dict")
        sliding_win = [0 for _ in range(token_config.UNIT_TIME_SIZE)]
        # 构建或者新的并发字典
        if token_config.CONTROL_ROT_CLS.token_concurrency_dict == {}:
            for i in self.token_data_list:
                # 判断是否是第一次初始化，由并发控制器接收数据
                token_config.CONTROL_ROT_CLS.token_concurrency_dict.update(
                    {i["token"]: {"ratelimit": i["ratelimit"], "surplus": i["ratelimit"],
                                  "ratelimit_mode": i["ratelimit_mode"],
                                  "ip_whitelist": i["ip_whitelist"], "ip_blacklist": i["ip_blacklist"],
                                  "data": i["data"], "type": i["type"], "sliding_win": sliding_win,
                                  "record": 0, "lock": i["lock"], "timeout": i["timeout"]}})
                token_config.TOKEN_TIMEOUT_DICT.update({i["token"]: i["timeout"], })
        else:
            for i in self.token_data_list:
                # 保存并发记录
                old_sliding_win = token_config.CONTROL_ROT_CLS.token_concurrency_dict[i["token"]]["sliding_win"]
                old_record = token_config.CONTROL_ROT_CLS.token_concurrency_dict[i["token"]]["record"]
                old_surplus = token_config.CONTROL_ROT_CLS.token_concurrency_dict[i["token"]]["surplus"]
                token_config.CONTROL_ROT_CLS.token_concurrency_dict.update(
                    {i["token"]: {"ratelimit": i["ratelimit"], "surplus": old_surplus,
                                  "ratelimit_mode": i["ratelimit_mode"],
                                  "ip_whitelist": i["ip_whitelist"], "ip_blacklist": i["ip_blacklist"],
                                  "data": i["data"], "type": i["type"], "sliding_win": old_sliding_win,
                                  "record": old_record, "lock": i["lock"], "timeout": i["timeout"]}})
                token_config.TOKEN_TIMEOUT_DICT.update({i["token"]: i["timeout"], })
        # 更新完成后更新本地最后更新时间
        token_config.LAST_UPDATA_TIME = int(time.time())
        print("update once db_data")


class RestToken:
    def __init__(self):
        # 初始化数据库对象
        self.db_opt = token_config.DB_OPTIONS_CLS
        # self.db_opt.test()
        # self.db_opt.test_type()
        # 初始化并发控制对象
        self.concurrency_rot = token_config.CONTROL_ROT_CLS
        print("中转token对象初始化")

    def get_token_date(self):
        """
        从数据库对象中拿到token数据并且创建token并发控制字典
        :return:
        """
        print("ready get_token_date")
        self.db_opt.db_get_token_date()


class control_rot:
    """
    并发控制器，通过滑动时间窗口的单位时间并发控制，数据采用优先级队列处理。
    """

    def __init__(self):
        # 优先级等待队列
        self.priority_waiting_queue = [[] for _ in range(0, token_config.PRIORITY_GRADE)]
        # token并发控制字典
        self.token_concurrency_dict = {}
        self.sum1 = 0
        print("并发控制器初始化")
        pass

    def cheak_token_legality(self, info: dict):
        """
        判断请求数据是否合法
        :param info: 请求数据
        :return:
        """
        try:
            # 判断数据类型是否合法
            if info["type"] in token_config.YAML_CONFIG["mongo_config"]["token_type_list"]:
                # 判断token是否存在
                if info["token"] in self.token_concurrency_dict:
                    token_info = self.token_concurrency_dict[info["token"]]
                    # 判断type是否正确
                    if token_info["type"] == info["type"]:
                        # 验证ip白名单黑名单
                        if token_info["ip_whitelist"]:
                            # 白名单不为空：判断ip是否在白名单中：
                            if info["ip"] in token_info["ip_whitelist"]:
                                self.blacklist_cheak(info, token_info)
                            else:
                                self.build_reject_res(info, "ip不在白名单")
                        else:
                            # 白名单为空直接判断是否在黑名单里
                            self.blacklist_cheak(info, token_info)
                else:
                    self.build_reject_res(info, "token不在字典中")
            else:
                self.build_reject_res(info, "token类型不在字典中")
        except Exception as e:
            self.build_reject_res(info, f"cheak_token_legality:error{e}")

    def blacklist_cheak(self, info, token_info):
        """
        判断是否在token黑名单或全局黑名单中
        :param info:
        :param token_info:
        :return:
        """
        if info["ip"] not in token_info["ip_blacklist"] and info["ip"] not in token_config.BLACK_LIST:
            """
            通过合法性验证,构建请求token进入到验证合法消费队列
            格式类型{type:str,token:str,ip:str,lock_ord:int,id:int,req_time:int}
            """
            info["token_info"] = token_info
            token_config.LEGAL_QUEUE.append(info)
            print("进入合法队列")
            # 通过合法性验证后返回int类型timeout时间，否则返回str类型报错信息
        else:
            self.build_reject_res(info, "ip在黑名单")

    @staticmethod
    def build_reject_res(data, info: str):
        token_config.REJECT_QUEUE.update({data["id"]: info})

    def consume_api_data(self):
        """
        处理接入待验证数据的队列里的数据的合法性
        :return:
        """
        while True:
            # 从队列中取到数据
            if len(token_config.API_DATA_QUEUE) != 0:
                info = token_config.API_DATA_QUEUE.pop(0)
                # 验证token合法性
                self.cheak_token_legality(info)
            else:
                time.sleep(token_config.SLEEP_TIME)

    def consume_legal_data(self):
        """
        请求数据经过合法性验证之后 请求接到合法队列里，这里主要消费合法数据 经过合法性验证后的构建的请求处理数据
        :return:
        """
        while True:
            # 从队列中取到数据
            if len(token_config.LEGAL_QUEUE) != 0:
                req_data = token_config.LEGAL_QUEUE.pop(0)
                token_info = req_data["token_info"]
                # 按照token的消费等级（用量计算）推送到等待消费优先级队列 （使用并发占比）
                if sum(token_info["sliding_win"]) == 0:
                    self.priority_waiting_queue[0].append(req_data)
                else:
                    grade = int((sum(token_info["sliding_win"]) / token_info["ratelimit"]) * 9.9)
                    print(f"grade:{grade}")
                    req_data["grade"] = grade
                    # 进入到优先级消费队列
                    self.priority_waiting_queue[grade].append(req_data)
                print("进入优先级队列")
            else:
                time.sleep(token_config.SLEEP_TIME)

    def consume_priority_data(self):
        """
        消费优先级队列里的数据
        :return:
        """
        while True:
            # 休眠机制遍历判断
            is_sleep = True
            # 遍历优先级队列
            for grade_queue in self.priority_waiting_queue:
                if grade_queue:
                    is_sleep = False
                    # 拿到数据后做处理，跳出循环 回到第一层遍历
                    handle_info = grade_queue.pop(0)
                    # 判断此时的请求时间是否超过timeout时间
                    if int(time.time()) - handle_info["req_time"] < handle_info["token_info"]["timeout"] * 60:
                        # 判断token的限制模式 0为等待 1为拒绝 2为锁模式
                        if handle_info["token_info"]["ratelimit_mode"] == 2:
                            self.lock_do_somthing(handle_info)
                        else:
                            # 并发模式判断该token是否有并发限制 0为无限制
                            if handle_info["token_info"]["ratelimit"] == 0:
                                self.bulid_res(handle_info)
                            else:
                                # 限制模式下判断该token是否还有余量
                                if handle_info["token_info"]["surplus"] > 0:
                                    self.concurrent_do_somthing(handle_info)
                                else:
                                    # 0等待模式
                                    if handle_info["token_info"]["ratelimit_mode"] == 0:
                                        # 返回合法队列
                                        token_config.LEGAL_QUEUE.append(handle_info)
                                    else:
                                        # 进入拒绝队列
                                        token_config.REJECT_QUEUE.update({handle_info["id"]: 0})
                    break
            if is_sleep:
                time.sleep(token_config.SLEEP_TIME)

    def concurrent_do_somthing(self, data):
        """
        并发模式的查询业务
        :return:
        """
        # 并发模式：单位时间内的并发记录 +1,剩余总量-1,返回结果
        data["token_info"]["record"] += 1
        data["token_info"]["surplus"] -= 1
        print(data["token_info"])
        self.bulid_res(data)

    def lock_do_somthing(self, data):
        """
        锁模式的查询业务
        :param data:
        :return:
        """
        # 检查该token是否有在上锁状态0为未上锁，上锁状态为1
        if data["token_info"]["lock"] == 1:
            if data["lock_ord"] == 0:  # 如果此时的lock命令是解锁
                data["token_info"]["lock"] = 0
                self.bulid_res(data)
            else:
                # 如果是请求加锁扔回验证合法队列
                token_config.LEGAL_QUEUE.append(data)
            time.sleep(1)
        else:
            # 上锁,并返回data
            data["token_info"]["lock"] = 1
            self.bulid_res(data)
        pass

    def bulid_res(self, data):
        """
        此处构建数据中转台返回到中转完成字典的数据
        :param data: 用于构建返回数据的原始信息
        """
        # 返回格式为{类id:data}
        token_config.DONE_QUEUE.update({data["id"]: data["token_info"]["data"]})
        self.sum1 += 1
        print(f"并发了{self.sum1}次")

    def concurrent_recode(self):
        """
        自动更新并发记录
        :return:
        """
        try:
            while True:
                time.sleep(1 / token_config.UNIT_TIME_SIZE)
                for token in list(self.token_concurrency_dict.keys()):
                    token_info = self.token_concurrency_dict[token]
                    # 抹除最后一条记录到剩余量,构建新的
                    new_surplus = token_info["surplus"] + token_info["sliding_win"][0]
                    # 记录列表前移,构建新的记录列表
                    new_sliding_win = token_info["sliding_win"][1:]
                    new_sliding_win.append(token_info["record"])
                    # 当前记录为重置为0
                    self.token_concurrency_dict[token].update(
                        {"surplus": new_surplus, "sliding_win": new_sliding_win, "record": 0})
        except Exception as e:
            print(f"e:{e}")

    def priority_up(self):
        """
        用于自动提升优先级队列的所有队列的优先级，免得有的请求一直沉底
        :return:
        """
        while True:
            # 按照配置文件设置的时间间隔坐休眠动作
            time.sleep(token_config.GRADE_UP_TIME)
            if token_config.PRIORITY_GRADE >= 2:
                # 第二级别与第一级别合并，最后一级补上空
                self.priority_waiting_queue[0].extend(self.priority_waiting_queue[1])
                self.priority_waiting_queue.pop(1)
                self.priority_waiting_queue.append([])
            else:
                # 只有一级 不做提升
                pass


def thread_tool(**kwargs):
    """
    线程守护工具，用于开启子线程和守护线程
    :return:
    """
    method_list = kwargs["method_list"]
    try:
        method_thread_list = {mothod.__name__: threading.Thread(target=mothod) for mothod in method_list}
        for name, method_thread in method_thread_list.items():
            method_thread.start()
            print(f"{name},线程启动")
        while True:
            # 判断线程是否存活，没存活就拉起来
            for name, method_thread in method_thread_list.items():
                if not method_thread.is_alive():
                    for mothod in method_list:
                        if name == mothod.__name__:
                            new_method_thread = threading.Thread(target=mothod)
                            new_method_thread.start()
                            print(f"拉起{name}线程")
            time.sleep(token_config.THREAD_CHEAK_TIME)
    except Exception as e:
        print(f"tread_tool error:{e}")


def main():
    # 初始化数据库操作对象
    token_config.DB_OPTIONS_CLS = DatabaseOptions()
    # 初始化并发控制系统对象
    token_config.CONTROL_ROT_CLS = control_rot()
    # 初始化数据中转台对象
    token_config.TOKEN_CLS = RestToken()
    # 要一直跑的方法列表
    method_list = [token_config.TOKEN_CLS.get_token_date, token_config.CONTROL_ROT_CLS.consume_api_data,
                   token_config.CONTROL_ROT_CLS.consume_legal_data, token_config.CONTROL_ROT_CLS.consume_priority_data,
                   token_config.CONTROL_ROT_CLS.concurrent_recode, token_config.CONTROL_ROT_CLS.priority_up]
    # method_list = [token_config.TOKEN_CLS.get_token_date,
    #                token_config.CONTROL_ROT_CLS.concurrent_recode, token_config.CONTROL_ROT_CLS.priority_up]
    # 传入方法名
    thread_tool_monitor = threading.Thread(target=thread_tool,
                                           kwargs={"method_list": method_list})
    thread_tool_monitor.start()


if __name__ == '__main__':
    # 传入request类中的data = {"type": "test", "token": "", "ip": ""}
    # 传入data经过补充后变成 {{"type": "test", "token": "", "ip": "",req_time:,lock_ord:""}
    # 类处理结束后为data = {"id"=int,"type": "test", "token": ""（带数据）, "ip": ""}

    # # 初始化数据库操作对象
    # token_config.DB_OPTIONS_CLS = DatabaseOptions()
    # # 初始化并发控制系统对象
    # token_config.CONTROL_ROT_CLS = control_rot()
    # # 初始化数据中转台对象
    # token_config.TOKEN_CLS = RestToken()
    # token_config.TOKEN_CLS.get_token_date()
    main()
