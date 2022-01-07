from os import environ as env
from sys import path
from os.path import dirname, abspath, join
from json import dumps
from uuid import UUID

path.append(join(dirname(abspath(__file__)), ".."))

from holoai_api import HoloAI_API
from aiohttp import ClientSession

from asyncio import run

if "HAI_USERNAME" not in env or "HAI_PASSWORD" not in env:
	raise RuntimeError("Please ensure that HAI_USERNAME and HAI_PASSWORD are set in your environment")

username = env["HAI_USERNAME"]
password = env["HAI_PASSWORD"]

async def main():
	async with ClientSession() as session:
		api = HoloAI_API(session)


		key = await api.high_level.login(username, password)
		await api.high_level.get_user_data(key, password)
#		print(dumps(await api.high_level.get_user_data(key), indent = 4))

run(main())