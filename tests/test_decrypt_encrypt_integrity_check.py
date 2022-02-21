from sys import path
from os import environ as env
from os.path import join, abspath, dirname

path.insert(0, abspath(join(dirname(__file__), '..')))

from holoai_api import HoloAI_API
from holoai_api.utils import format_and_decrypt_stories, encrypt_and_format_stories


from aiohttp import ClientSession
from base64 import b64encode

from asyncio import run

from typing import List, Dict, Any

def compare_in_out(type_name: str, items_in: List[Dict[str, Any]], items_out: List[Dict[str, Any]]) -> bool:
    fail_flags = ''.join(('O' if item_in == item_out else 'X') for item_in, item_out in zip(items_in, items_out))
    if 'X' in fail_flags:
        print(f"{fail_flags.count('X')}/{len(fail_flags)} integrity checks failed for {type_name}")
        print(fail_flags)
        print("")

        return False
    else:
        print(f"All {len(fail_flags)} integrity checks succeeded for {type_name}\n")
        return True

if "HAI_USERNAME" not in env or "HAI_PASSWORD" not in env:
    raise RuntimeError("Please ensure that HAI_USERNAME and HAI_PASSWORD are set in your environment")

username = env["HAI_USERNAME"]
password = env["HAI_PASSWORD"]

async def stories_integrity(api: HoloAI_API):
    api.timeout = 30

    account_key = await api.high_level.login(username, password)

    user = await api.high_level.get_user_data()
    stories = user["stories"]

    encrypted_stories_in = [str(story) for story in stories]
    format_and_decrypt_stories(account_key, *stories)
    encrypt_and_format_stories(account_key, *stories)
    encrypted_stories_out = [str(story) for story in stories]

    assert compare_in_out("stories", encrypted_stories_in, encrypted_stories_out)

async def test_stories_integrity_sync():
    # sync handler
    api = HoloAI_API()
    await stories_integrity(api)

async def test_stories_integrity_async():
    # async handler
    try:
        async with ClientSession() as session:
            api = HoloAI_API(session)
            await stories_integrity(api)
    except Exception as e:
        await session.close()
        raise e


if __name__ == "__main__":
    async def main():
        await test_stories_integrity_async()

    run(main())