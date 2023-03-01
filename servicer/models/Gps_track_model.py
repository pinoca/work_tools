import mongoengine

mongoengine.connect("mws")


class Gps_track(mongoengine.DynamicDocument):
	# GPS
	gps_id = mongoengine.IntField(max_length=10, required=True, default=0)
	# 经度
	lng = mongoengine.StringField()
	# 纬度
	lat = mongoengine.StringField()
	# 基站
	bs = mongoengine.StringField(max_length=100)
	# 温度
	temp = mongoengine.StringField()
	# 国家代码
	c_code = mongoengine.StringField(max_length=10)
	# 地址
	addr = mongoengine.ListField()
	# 报文
	data = mongoengine.ListField()
	# 创建时间
	created = mongoengine.IntField(max_length=10)


