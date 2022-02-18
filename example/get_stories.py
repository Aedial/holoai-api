from os import environ as env
from sys import path
from os.path import dirname, abspath, join
from json import dumps

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

        account_key = await api.high_level.login(username, password)
        stories = await api.high_level.get_stories(account_key)
        print(dumps(stories, indent = 4))

        print("")

        for story in stories:
            story_id = story["id"]

            print("\nStory:")
            story = await api.high_level.get_story(story_id, account_key)
            print(dumps(story, indent = 4))

            print("\nSnapshots:")
            snapshots = await api.low_level.read_snapshots(story_id)
            print(dumps(snapshots, indent = 4))

            print("")

run(main())