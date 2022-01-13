from os import environ as env, listdir
from sys import path
from os.path import dirname, abspath, join
from json import dumps
from asyncio import run
from argparse import ArgumentParser
from math import ceil
from tqdm import tqdm
from time import sleep

path.append(join(dirname(abspath(__file__)), ".."))

from holoai_api import HoloAI_API
from aiohttp import ClientSession

from typing import Union

def format_file_size(size: Union[float, int, str]) -> str:
    """Return the given bytes as a human friendly KB, MB, GB, or TB string."""
    size = float(size)

    KB = float(1024 ** 1)
    MB = float(1024 ** 2)
    GB = float(1024 ** 3)
    TB = float(1024 ** 4)

    if TB <= size:
        return f"{size/TB:.2f} TB"
    elif GB <= size < TB:
        return f"{size/GB:.2f} GB"
    elif MB <= size < GB:
        return f"{size/MB:.2f} MB"
    elif KB <= size < MB:
        return f"{size/KB:.2f} KB"
    else:
        return f"{size} B"

def format_time(t: Union[float, int]) -> str:
    ms = f" {int(t * 1000) % 1000} ms" if type(t) is float else ""
    t = int(t)

    mins = 60
    hours = 60 * 60

    if t < mins:
        return f"{t} secs{ms}"
    elif t < hours:
        return f"{int(t / mins)} mins {t % mins} secs"
    else:
        return f"{int(t / hours)} hours {int(t / mins) % mins} mins"

if "HAI_USERNAME" not in env or "HAI_PASSWORD" not in env:
    raise RuntimeError("Please ensure that HAI_USERNAME and HAI_PASSWORD are set in your environment")

username = env["HAI_USERNAME"]
password = env["HAI_PASSWORD"]

async def main():
    async with ClientSession() as session:
        api = HoloAI_API(session)
        Prefix = api.low_level.Prefix
        Listing = api.low_level.Listing

        account_key = await api.high_level.login(username, password)

        size = 0
        documents = []
        for filename in listdir(args.directory):
            with open(join(args.directory, filename)) as f:
                data = f.read()
                documents.append({ "filename": filename, "text": data })
                size += len(data)

        percentage = float(args.percentage)
        prefix = { "novel": Prefix.Novel, "fanfic": Prefix.Fanfic, "romance": Prefix.Romance, "cyoa": Prefix.CYOA, "generic": Prefix.Generic }[args.prefix]
        visibility = { "private": Listing.Private, "unlisted": Listing.Unlisted, "public": Listing.Public }[args.visibility]

        dataset = await api.low_level.create_prompt_tune_dataset(args.name, documents)
        dataset_id = dataset["id"]
        dataset_size = sum(d["tokensLength"] for d in dataset["documents"])

        steps = ceil(dataset_size / 8192 * percentage / 100)
        checkpoints = [ *range(0, steps, 20), steps ]

        try:
            print(f"Training module {args.name} for {steps} steps ({format_file_size(size)})")
            module = await api.low_level.create_prompt_tune(checkpoints,
                                                            dataset_id,
                                                            args.description,
                                                            True,
                                                            visibility,
                                                            api.low_level.ModelName.Model,
                                                            args.nsfw,
                                                            steps,
                                                            prefix,
                                                            [],
                                                            args.name)
        except Exception as e:
            await api.low_level.delete_prompt_tune_dataset(dataset_id)
            raise e

        tune_id = module["id"]

        print(f"Module queued with id {tune_id}")

        progress = tqdm(total = steps, unit = "step")
        progress.set_description("Queued, waiting for training")

        while True:
            state = await api.low_level.read_prompt_tune(tune_id)

            run_state = state["data"]["runStatus"]
            if run_state is None:
                break

            cur_steps = run_state["currentStepNo"]
            if cur_steps == 0:
                progress.refresh()
                sleep(5)
            else:
                progress.n = cur_steps
                progress.set_description("Training")
                sleep(1)

        progress.n = steps
        progress.set_description("Finished")
        progress.close()

        created_at = int(state["data"]["createdAt"] / 1000)
        started_at = state["data"]["startedAt"]
        finished_at = state["data"]["finishedAt"]

        wait = started_at - created_at
        train = finished_at - started_at

        print(f"Waited {format_time(wait)} in queue, then trained for {format_time(train)}")

        loss_file = f"{args.name} loss.csv" if ' ' in args.name else f"{args.name}_loss.csv"
        with open(loss_file, "w") as f:
            print(*state["data"]["trainLossByStep"], sep = ',', end = '', file = f)

parser = ArgumentParser()
parser.add_argument("name", help = "Name of the module")
parser.add_argument("directory", help = "Path to the directory of the files to be included")
parser.add_argument("prefix", choices = ["novel", "fanfic", "romance", "generic"], help = "Prefix name")
parser.add_argument("visibility", choices = ["private", "unlisted", "public"], help = "Visibility of the module")
parser.add_argument("-d", "--description", nargs = '?', default = "", help = "Description of the module. Default to empty")
parser.add_argument("-p", "--percentage", nargs = '?', default = "100.0", help = "Percentage of the dataset to use (100.0 is 100%%). Default is 100%%")
parser.add_argument("-n", "--nsfw", action = "store_true", help = "Is the module NSFW")
args = parser.parse_args()

run(main())