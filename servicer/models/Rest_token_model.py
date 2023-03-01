import mongoengine

mongoengine.connect("dev")


class Rest_token(mongoengine.DynamicDocument):
	# 类型
	type = mongoengine.StringField(max_length=100)
	# TOKEN
	token = mongoengine.StringField(max_length=100)
	# 限速
	ratelimit = mongoengine.IntField(max_length=10, required=True, default=0)
	# 超限制处理模式 0为等待 1为拒绝 2为锁模式
	ratelimit_mode = mongoengine.IntField(max_length=10, required=True, default=1)
	# 上锁状态 1为上锁 0为无锁
	lock = mongoengine.IntField(max_length=10, required=True, default=0)
	# 超时时间 单位时间分钟
	timeout = mongoengine.IntField(max_length=10, required=True, default=3)
	# ip白名单
	ip_whitelist = mongoengine.ListField()
	# ip黑名单
	ip_blacklist = mongoengine.ListField()
	# 数据
	data = mongoengine.ListField()
	# 最后更新
	updated = mongoengine.IntField(max_length=10)
	# 创建时间
	created = mongoengine.IntField(max_length=10)


