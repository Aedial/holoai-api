from sys import path
from os import environ as env
from os.path import join, abspath, dirname

path.insert(0, abspath(join(dirname(__file__), '..')))

from holoai_api import HoloAI_API
from holoai_api.Tokenizer import Tokenizer
from holoai_api.types import Model, Prefix

from aiohttp import ClientSession
from logging import Logger, StreamHandler
from typing import Union, List, Tuple

import pytest
import asyncio

def permutations(*args):
    args = [list(a) for a in args if len(a)]
    l = len(args)
    ilist = [0] * l

    while True:
        yield [arg[i] for arg, i in zip(args, ilist)]

        ilist[0] += 1
        for i in range(l):
            if ilist[i] == len(args[i]):
                if i + 1 == l:  # end, don't overflow
                    return
                else:
                    ilist[i + 1] += 1
                    ilist[i] = 0
            else:
                break

if "HAI_USERNAME" not in env or "HAI_PASSWORD" not in env:
    raise RuntimeError("Please ensure that HAI_USERNAME and HAI_PASSWORD are set in your environment")

username = env["HAI_USERNAME"]
password = env["HAI_PASSWORD"]

logger = Logger("HoloAI")
logger.addHandler(StreamHandler())

input_txt = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Aliquam at dolor dictum, interdum est sed, consequat arcu. Pellentesque in massa eget lorem fermentum placerat in pellentesque purus. Suspendisse potenti. Integer interdum, felis quis porttitor volutpat, est mi rutrum massa, venenatis viverra neque lectus semper metus. Pellentesque in neque arcu. Ut at arcu blandit purus aliquet finibus. Suspendisse laoreet risus a gravida semper. Aenean scelerisque et sem vitae feugiat. Quisque et interdum diam, eu vehicula felis. Ut tempus quam eros, et sollicitudin ligula auctor at. Integer at tempus dui, quis pharetra purus. Duis venenatis tincidunt tellus nec efficitur. Nam at malesuada ligula."
input = [input_txt]
tokenize_input = [False, True]

models = [*Model]
prefixes = [*Prefix]

model_input_prefix_permutation = [*permutations(models, input, prefixes, tokenize_input)]

async def simple_generate(api: HoloAI_API, model: Model, input: str, prefix: Prefix, tokenize: bool):
    await api.high_level.login(username, password)

    logger.info(f"Using model {model.value} and prefix {prefix.name}\n")

    if tokenize:
        input = Tokenizer.encode(model, input)

    gen = await api.low_level.draw_completions(input, model, prefix)
    logger.info(gen)
#    logger.info(Tokenizer.decode(model, b64_to_tokens(gen["output"])))

@pytest.mark.parametrize("model,input,prefix,tokenize", model_input_prefix_permutation)
async def test_simple_generate_sync(model: Model, input: str, prefix: Prefix, tokenize: bool):
    # sync handler
    api = HoloAI_API()
    await simple_generate(api, model, input, prefix, tokenize)

@pytest.mark.parametrize("model,input,prefix,tokenize", model_input_prefix_permutation)
async def test_simple_generate_async(model: Model, input: str, prefix: Prefix, tokenize: bool):
    # async handler
    async with ClientSession() as session:
        api = HoloAI_API(session)
        await simple_generate(api, model, input, prefix, tokenize)