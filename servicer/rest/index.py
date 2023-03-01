import json

from servicer.common import rest_return
import random

num = 0
num1 = 0


def default_index(**kwargs):
    res = "default_index"
    return rest_return.success(data=res)


def asynctest(**kwargs):
    n = random.random()
    global num
    global num1
    num += 1
    print(f"num:{num},num1:{num1}")
    if n < 0.6:
        num1 += 1
        return rest_return.success_tms()
    else:
        return rest_return.error_tms()
