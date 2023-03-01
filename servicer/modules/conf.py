# coding=utf-8
import threading
import time
import pymongo

# 从配置文件的读入的conf字段
# config = {}
# 缓存的读入
cache = {}
m_mongodb_ip = ""
m_mongodb_port = ""
# 需要用户名和密码进行身份认证的数据库,如果没对数据库单独上锁就用root账号密码
m_mongodb_authSource = ""
# 用户名
m_mongodb_username = ""
# 密码
m_mongodb_password = ""
# 默认转接端口
s_mongodb_port = ""
# app前缀字典
db_prefix_dict = {}
# 请求过的appid,code字典
appcode_recode_list = []


def read_db_data_to_cache(req_appid, req_appcode, table_name, req_field_list):
    """
    读取配置中定好需要的数据库数据到缓存中
    :param req_field_list: 请求表的所有字段
    :param table_name: 表名称
    :param req_appcode: app数据库名称
    :param req_appid: app唯一代码
    :return:
    """
    try:
        if m_mongodb_authSource:
            db_connect_str = "mongodb://" + m_mongodb_username + ":" + m_mongodb_password + "@" + m_mongodb_ip + ":" + m_mongodb_port + "/?authSource=" + m_mongodb_authSource
        else:
            if m_mongodb_username and m_mongodb_password:
                db_connect_str = "mongodb://" + m_mongodb_username + ":" + m_mongodb_password + "@" + m_mongodb_ip + ":" + m_mongodb_port + "/"
            else:
                db_connect_str = "mongodb://" + m_mongodb_ip + ":" + m_mongodb_port + "/"
        # 连接主服务器
        client = pymongo.MongoClient(db_connect_str)
        # 连接app表寻找app在局域网内的ip和构建真实数据库名称
        collection = client["parcelc"]["app"]
        app_info_data = collection.find({"code": req_appcode})[0]
        app_db_host = app_info_data["db_host"]
        updated = app_info_data["updated"]
        # 找内网ip
        collection = client["parcelc"]["server_cluster"]
        db_intranets_ip = collection.find({"code": app_db_host})[0]["intranets"]
        client.close()
        # 连接存储数据服务器的数据库
        r_db_connect_str = "mongodb://" + db_intranets_ip + ":" + s_mongodb_port + "/"
        r_client = pymongo.MongoClient(r_db_connect_str)
        # 存储数据
        r_dbname = db_prefix_dict.get(req_appid, "") + req_appcode
        r_collection = r_client[r_dbname][table_name]
        table_data = r_collection.find()
        # 初始化一个表缓存空间
        cache[r_dbname] = {}
        cache[r_dbname][table_name] = {}
        table_field_list = req_field_list
        # 遍历表
        for table_info in table_data:
            # 存储为{"id":{file,file}}
            var_cache = {}
            for file in table_field_list:
                try:
                    var_cache[file] = table_info[file]
                except Exception as e:
                    var_cache[file] = "N/A"
                # 存储到缓存中的是真实数据库名称
                cache[r_dbname][table_name].update({str(table_info["_id"]): var_cache})
        r_client.close()
        # 添加记录[{appid:req_appid,app_code:req_appcode,appid:req_appid}]
        appcode_recode_list.append(
            {"appid": req_appid, "appcode": req_appcode, "dbname": r_dbname, "intranets_ip": db_intranets_ip, "table_name": table_name, "req_field_list": req_field_list, "updated": updated})
        return True, 1
    except Exception as e:
        return False, e


def check_cache(**kwargs):
    """
    这个用与查询缓存
    :param kwargs:
        req_data:dict 用于接收请求的数据
    :return:
    """
    # 取出请求参数
    req_conf = kwargs["req_data"]["conf"]
    req_appid = kwargs["req_data"]["appid"]
    req_appcode = kwargs["req_data"]["appcode"]
    req_field_list = []
    # 去数据库查询的控制变量
    # 遍历需要查询的表
    cache_exist = False
    a = cache
    r_dbname = db_prefix_dict.get(req_appid, "") + req_appcode
    for req_table_name, t_value in req_conf.items():
        # 拿到所需的所有字段
        req_field_list.extend(kwargs["req_data"]["conf"][req_table_name]["selectValue"])
        req_field_list.extend(kwargs["req_data"]["conf"][req_table_name]["valuesKeys"])
        var_set = set(req_field_list)
        req_field_list = list(var_set)
        # 检查缓存中是否存在,缓存是否有这个appid，库和表
        if cache.get(r_dbname, ""):
            if cache[r_dbname].get(req_table_name, ""):
                for recode_info in appcode_recode_list:
                    if r_dbname == recode_info["dbname"] and req_table_name == recode_info["table_name"]:
                        if req_field_list == recode_info["req_field_list"]:
                            cache_exist = True
                            break
        # 缓存中没有直接去更新去数据库更新
        if not cache_exist:
            read_static, read_info = read_db_data_to_cache(req_appid, req_appcode, req_table_name, req_field_list)
            if not read_static:
                print(read_info)
        key_list = kwargs["req_data"]["conf"][req_table_name]["key"]
        # 字段下拉
        if "selectValue" in kwargs["req_data"]["conf"][req_table_name]:
            # 选择字段列表
            select_filed_list = kwargs["req_data"]["conf"][req_table_name]["selectValue"]
            select_res = get_selectValue(key_list, select_filed_list, r_dbname, req_table_name)
            kwargs["req_data"]["conf"][req_table_name]["selectValue"] = select_res
        if "valuesKeys" in kwargs["req_data"]["conf"][req_table_name]:
            # 选择字段列表
            valuesKeys_filed_list = kwargs["req_data"]["conf"][req_table_name]["valuesKeys"]
            valuesKeys_filed_list_res = get_values(key_list, valuesKeys_filed_list, r_dbname, req_table_name)
            kwargs["req_data"]["conf"][req_table_name]["valuesKeys"] = valuesKeys_filed_list_res
    res = kwargs["req_data"]
    return res


def get_selectValue(key_list, filed_list, db_name, table_name):
    """
    下拉列表返回结构构造
    :param key_list: id 列表
    :param filed_list: 字段 列表
    :param db_name: 数据库名称
    :param table_name: 表名称
    :return: 返回构造好的列表
    """
    res = {}
    # 遍历字段
    for filed in filed_list:
        res[filed] = []
        for key in key_list:
            try:
                res[filed].append({key: cache[db_name][table_name][key][filed]})
            except Exception as e:
                res[filed].append({key: "N/A"})
    return res


def get_values(key_list, filed_list, db_name, table_name):
    """
    值列表返回结构构造{{id:{filed:filed_value}}}
    :param key_list: id 列表
    :param filed_list: 字段 列表
    :param db_name: 数据库名称
    :param table_name: 表名称
    :return: 返回构造好的列表
    """
    res = {}
    # 遍历key再遍历字段
    for key in key_list:
        res[key] = {}
        try:
            data = cache[db_name][table_name][key]
            for filed in filed_list:
                if filed in data:
                    res[key].update({filed: data[filed]})
                else:
                    res[key].update({filed: "N/A"})
        except Exception as e:
            for filed in filed_list:
                res[key].update({filed: "N/A"})
    return res


def db_update_thread():
    """
    每隔一秒更新缓存中的数据
    :return:
    """
    while True:
        try:
            if m_mongodb_authSource:
                db_connect_str = "mongodb://" + m_mongodb_username + ":" + m_mongodb_password + "@" + m_mongodb_ip + ":" + m_mongodb_port + "/?authSource=" + m_mongodb_authSource
            else:
                if m_mongodb_username and m_mongodb_password:
                    db_connect_str = "mongodb://" + m_mongodb_username + ":" + m_mongodb_password + "@" + m_mongodb_ip + ":" + m_mongodb_port + "/"
                else:
                    db_connect_str = "mongodb://" + m_mongodb_ip + ":" + m_mongodb_port + "/"
            # 连接主服务器
            client = pymongo.MongoClient(db_connect_str)
            # 连接app表寻找app在局域网内的ip和构建真实数据库名称
            collection = client["parcelc"]["app"]
            while True:
                # 遍历记录表查看是否有更新
                for recode_info in appcode_recode_list:
                    db_update_time = collection.find({"code": recode_info["appcode"]})[0]["updated"]
                    if recode_info["updated"] != db_update_time:
                        # 发现库更新，so去更新这个库里面的表格
                        recode_info["updated"] = db_update_time
                        # 连接存储数据库
                        up_connect_str = "mongodb://" + recode_info["intranets_ip"] + ":" + s_mongodb_port + "/"
                        up_client = pymongo.MongoClient(up_connect_str)
                        up_collection = up_client[recode_info["dbname"]][recode_info["table_name"]]
                        table_data = up_collection.find()
                        # 要更新的字段
                        table_field_list = recode_info["req_field_list"]
                        # 遍历表
                        for table_info in table_data:
                            # 存储为{"id":{file,file}}
                            var_cache = {}
                            for file in table_field_list:
                                try:
                                    var_cache[file] = table_info[file]
                                except Exception as e:
                                    var_cache[file] = "N/A"
                                # 存储到缓存中的是真实数据库名称
                                cache[recode_info["dbname"]][recode_info["table_name"]].update({str(table_info["_id"]): var_cache})
                        up_client.close()
                time.sleep(1)
        except Exception as e:
            print(f"更新失败：{e}")
            pass
        time.sleep(2)


db_update = threading.Thread(target=db_update_thread)
db_update.start()

if __name__ == '__main__':
    pass
