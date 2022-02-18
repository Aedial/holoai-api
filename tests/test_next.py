# Verify all the requests using the _next framework work

from os import environ as env
from sys import path
from os.path import dirname, abspath, join
from asyncio import run
from aiohttp import ClientSession
from json import dumps

path.append(join(dirname(abspath(__file__)), ".."))

from holoai_api import HoloAI_API

if "HAI_USERNAME" not in env or "HAI_PASSWORD" not in env:
    raise RuntimeError("Please ensure that HAI_USERNAME and HAI_PASSWORD are set in your environment")

username = env["HAI_USERNAME"]
password = env["HAI_PASSWORD"]

async def get_next(api: HoloAI_API):
        account_key = await api.high_level.login(username, password)

        print(dumps(await api.low_level.get_home(), indent = 4))
#        print(await api.low_level.get_story(story_id))
        print(dumps(await api.low_level.get_tunes(), indent = 4))

async def test_get_next_async():
    try:
        async with ClientSession() as session:
            api = HoloAI_API(session)
            await get_next(api)
    except Exception as e:
        await session.close()
        raise e

async def test_get_next_sync():
    api = HoloAI_API()
    await get_next(api)

if __name__ == "__main__":
    run(test_get_next_sync())