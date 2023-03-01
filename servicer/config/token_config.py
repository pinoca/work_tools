# mongodb的配置类型
MONGODB_CONFIG_TYPE = "mongo_config"

# 配置yaml文件
YAML_CONFIG = {}

# 全局黑名单
BLACK_LIST = []

# 接入待验证数据的队列[]
API_DATA_QUEUE = []

# 验证完数据合法性的队列[]
LEGAL_QUEUE = []

# token的timeout字典
TOKEN_TIMEOUT_DICT = {}

# 滑动窗口单位时间分块数量
UNIT_TIME_SIZE = 5

# 完成的数据中转的字典{类id：结果}
DONE_QUEUE = {}

# 拒绝并发请求的字典{}
REJECT_QUEUE = {}
# token中转台类
TOKEN_CLS = object

# 数据库操作类
DB_OPTIONS_CLS = object

# 并发控制类
CONTROL_ROT_CLS = object

# 数据中转时等待轮询中转结果的间隔
TRANSIT_WAIT_TIME = 0.5

# 并发控制的优先级等待队列的级数
PRIORITY_GRADE = 10

# 提升优先级队列中各队列优先级的间隔时间
GRADE_UP_TIME = 10

# 向数据空轮询访问的间隔时间设置
DB_VIST_TIME = 10

# 最后一次更新时间 为10位时间戳
LAST_UPDATA_TIME = 0

# 守护线程的拉起检查时间
THREAD_CHEAK_TIME = 5

# 空闲时间隔休息时间
SLEEP_TIME = 0.5
