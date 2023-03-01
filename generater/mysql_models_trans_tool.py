import pymysql
import yaml


class Configure:
    """
    加载配置信息类
    :return 返回对应配置信息,字典格式
    """

    def __init__(self):
        # 加载yaml配置文件
        with open("config.yaml", "r", encoding="utf-8") as f:
            self.conf = yaml.load(f.read(), Loader=yaml.FullLoader)

    def get_mysqldb_config(self):
        return self.conf["mysql_config"]

    def get_trans_conf(self):
        return self.conf["trans_conf"]

    def get_mongo_config(self):
        return self.conf["mongo_config"]


class MysqlConnect:
    """
    主要用此类与数据库进行交互，执行增删查的sql语句
    :return 查询返回全部的查询结果，增删查成功返回1，失败返回0
    """

    def __init__(self, host, port, user, pwd, database, charset):
        # 连接数据库建立游标
        self.db = pymysql.connect(
            host=host,
            port=port,
            user=user,
            passwd=pwd,
            database=database,
            charset=charset,
        )
        self.cursor = self.db.cursor()

    # 执行查询sql
    def query(self, sql):
        self.cursor.execute(sql)
        res = self.cursor.fetchall()
        return res

    # 执行增删查sql
    def update(self, sql):
        try:
            self.cursor.execute(sql)
            self.db.commit()
            return 1
        except Exception as e:
            print(e)
            self.db.rollback()
            return 0

    # 关闭数据库连接和游标
    def close(self):
        self.cursor.close()
        self.db.close()


class ExportMysqlTable(object):
    """
    此类主要作用是把表结构转换成mongodbengine的模型文件
    :return
    get_all_tables()返回所有数据库表名称
    struct_of_table_generator()返回数据库表结构
    """

    def __init__(self):
        # 配置
        self.conf = Configure().get_mysqldb_config()
        self.trans_conf = Configure().get_trans_conf()
        # 连接mysql数据库
        self.con = MysqlConnect(
            self.conf["host"],
            self.conf["port"],
            self.conf["username"],
            self.conf["password"],
            self.conf["db_names"][0],
            self.conf["charset"],
        )

    def get_all_tables(self):  # 查询所有表,并返回配置里需要的表名称.
        res = self.con.query("SHOW TABLES")
        tb_list = []
        target = self.trans_conf["target_table"]
        for item in res:
            if target != []:
                if item[0] in target:
                    tb_list.append(item[0])
            else:
                tb_list.append(item[0])
        return tb_list

    def struct_of_table_generator(self):

        tb_list = self.get_all_tables()  # 拿到所有表名称
        for index, tb_name in enumerate(tb_list):
            # 拿到表创建代码并处理存入字典中
            sql = "show full fields from {}".format(tb_name)
            # 输出元组(字段名，类型，属于的集合，是否为空，是否是主键，默认值，extra，privileges，注释)
            tb_list[index] = {tb_name: self.con.query(sql)}
        return tb_list

    def trans_to_mongo(self):
        typedict = {
            "text": "ListField",
            "int": "IntField",
            "varchar": "StringField",
            "float": "StringField",
        }  # 转换字典
        trans = Configure().get_trans_conf()
        limit = ""  # 字段的限制条件
        tb_list = self.struct_of_table_generator()  # 拿到所有表结构
        for i in range(len(tb_list)):
            for key, values in tb_list[i].items():
                key_sum = 1
                name = key[0].upper() + key[1:]

                # w的意思:打开一个文件只用于写入。如果该文件已存在则打开文件，并从开头开始编辑，即原有内容会被删除。如果该文件不存在，创建新文件
                op = open(trans["save_dir"] + name + "_model.py", "w", encoding="utf8")
                op.write(
                    """import mongoengine\n\nmongoengine.connect("{}")\n\n\n""".format(
                        self.conf["db_names"][0]
                    )
                )
                op.write("class {}(mongoengine.DynamicDocument):\n\t".format(name))
                for index, value in enumerate(values):
                    # 判断是否有长度限制
                    if value[0] == "_id":
                        key_sum += 1
                        continue
                    if value[1].find("(") != -1:
                        if value[1][: value[1].find("(")] == "float":
                            t_type = typedict[value[1][: value[1].find("(")]]
                        else:
                            maxlen = value[1][
                                     value[1].find("(") + 1: value[1].find(")")
                                     ]
                            if limit != "":
                                limit += ", "
                            limit += "max_length={}".format(maxlen)
                            t_type = typedict[value[1][: value[1].find("(")]]
                    else:
                        t_type = typedict[value[1]]

                    # 判断空值和默认值
                    if value[3] == "NO":
                        if value[5] is None:
                            if limit != "":
                                limit += ", "
                            limit += "required=True"
                        else:
                            if limit != "":
                                limit += ", "
                            limit += "required=True, default={}".format(value[5])
                    if key_sum == len(values):
                        op.write(
                            """# {}\n\t{} = mongoengine.{}({})\n\n\n""".format(
                                value[8], value[0], t_type, limit
                            )
                        )
                    else:
                        op.write(
                            """# {}\n\t{} = mongoengine.{}({})\n\t""".format(
                                value[8], value[0], t_type, limit
                            )
                        )
                    limit = ""
                    key_sum += 1
                op.close()


if __name__ == "__main__":
    con = ExportMysqlTable()
    con.trans_to_mongo()
    print("生成完成")
