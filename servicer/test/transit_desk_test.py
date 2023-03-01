import requests
import json

# async def main():
#     url = "http://localhost:23134"
#
#     payload = json.dumps({
#         "type": "test",
#         "token": "test0",
#         "ip": "111222",
#         "lock_ord": 0
#     })
#     headers = {
#         'Content-Type': 'application/json'
#     }
#     while True:
#         response = requests.request("POST", url, headers=headers, data=payload)
#
#         print(response.text)


import asyncio, aiohttp  # 导入库


async def get_url(url):
    payload = json.dumps({
        "type": "test",
        "token": "test0",
        "ip": "111222",
        "lock_ord": 0
    })
    headers = {
        'Content-Type': 'application/json'
    }
    session = aiohttp.ClientSession()  # 确定clien对象
    while True:
        res = await session.post(url, data=payload, headers=headers)  # 异步等待
        await res.text()
        print(res.text())


async def request():
    url = "http://localhost:23134"  # 该网站爬取十次不用异步需要六十秒
    await get_url(url)


tasks = [asyncio.ensure_future(request()) for i in range(10000)]  # 列表解析式
loop = asyncio.get_event_loop()
loop.run_until_complete(asyncio.wait(tasks))
