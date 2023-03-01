import mongoengine

mongoengine.connect("mws")


class Tracker(mongoengine.DynamicDocument):
	# token表的id主键
	token_id = mongoengine.StringField(max_length=100)
	# 快递公司代码
	carrier_code = mongoengine.StringField(max_length=100, required=True)
	# 跟踪号
	tracking_number = mongoengine.StringField(max_length=100, required=True)
	# 签收人
	signed_name = mongoengine.StringField(max_length=100)
	# 路由信息
	traces = mongoengine.ListField()
	# 同步次数
	sync_count = mongoengine.IntField(max_length=10)
	# 同步失败次数
	sync_failure_count = mongoengine.IntField(max_length=10)
	# 状态
	status = mongoengine.StringField(max_length=100)
	# api平台
	api_from = mongoengine.StringField(max_length=100)
	# 查询账号
	api_account_id = mongoengine.StringField(max_length=100)
	# 下单时间
	order_time = mongoengine.IntField(max_length=10, required=True, default=0)
	# 提取时间
	pickup_time = mongoengine.IntField(max_length=10, required=True, default=0)
	# 签收时间
	delivered_time = mongoengine.IntField(max_length=10, required=True, default=0)
	# 下次更新时间
	next_update_time = mongoengine.IntField(max_length=10, required=True, default=0)
	# 最后同步时间
	updated = mongoengine.IntField(max_length=10, required=True, default=0)
	# 创建时间
	created = mongoengine.IntField(max_length=10, required=True, default=0)


