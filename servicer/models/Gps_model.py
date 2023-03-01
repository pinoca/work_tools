import mongoengine

mongoengine.connect("mws")


class Gps(mongoengine.DynamicDocument):
	# 自增ID
	inc_id = mongoengine.IntField(max_length=10, required=True)
	# 客户
	user_id = mongoengine.IntField(max_length=10)
	# 供应商ID
	supplier_id = mongoengine.IntField(max_length=10)
	# 供应商型号
	supplier_model = mongoengine.StringField(max_length=100)
	# 供应商编码
	supplier_number = mongoengine.StringField(max_length=100)
	# 产品型号
	model = mongoengine.StringField(max_length=100)
	# 系统编号
	number = mongoengine.StringField(max_length=100, required=True)
	# IMEI
	imei = mongoengine.StringField(max_length=100)
	# 状态
	status = mongoengine.IntField(max_length=10, required=True, default=0)
	# 标签
	tags = mongoengine.ListField()
	# 信息数
	msg_count = mongoengine.IntField(max_length=10, required=True, default=0)
	# SN编号
	sn_code = mongoengine.StringField(max_length=100)
	# 最后路由时间
	active_time = mongoengine.IntField(max_length=10, required=True, default=0)
	# 更新时间
	update_time = mongoengine.IntField(max_length=10, required=True, default=0)
	# 创建时间
	created = mongoengine.IntField(max_length=10, required=True, default=0)
	# 过期时间
	expire_time = mongoengine.IntField(max_length=10)
	# 交付时间
	transaction_time = mongoengine.IntField(max_length=10)
	# 采购批次
	purchase_id = mongoengine.IntField(max_length=10)
	# 销售批次
	sell_id = mongoengine.IntField(max_length=10)
	# 参考号1
	ref_1 = mongoengine.StringField(max_length=255)
	# 参考号2
	ref_2 = mongoengine.StringField(max_length=255)
	# 参考号3
	ref_3 = mongoengine.StringField(max_length=255)


