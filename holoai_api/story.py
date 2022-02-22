from holoai_api import HoloAI_API
from holoai_api.utils import encrypt_user_data, decrypt_user_data, b64_to_tokens
from holoai_api.types import Model
from holoai_api.Tokenizer import Tokenizer
from holoai_api.BanList import BanList
from holoai_api.BiasGroup import BiasGroup
from holoai_api.Preset import Preset
from holoai_api.GlobalSettings import GlobalSettings

from copy import deepcopy
from time import time
from json import loads, dumps
from enum import Enum, auto

from typing import Dict, Iterator, List, NoReturn, Any, Optional, Union, Iterable, Tuple

def _get_time() -> int:
    """
    Get the current time, as formatted for createdAt and lastUpdatedAt

    :return: Current time with millisecond precision
    """

    return int(time() * 1000)

def _get_short_time() -> int:
    """
    Because some lastUpdatedAt only are precise to the second

    :return: Current time with second precision
    """

    return int(time())

def _set_nested_item(item: Dict[str, Any], val: Any, path: str):
    path = path.split('.')

    for key in path[:-1]:
        item = item[key]

    item[path[-1]] = val

class Story_DataFragmentOrigin:
    Prompt = auto() # base (allow EDIT block referencing index 0)
    AI = auto()     # generation
    Edit = auto()   # edit by user

class HoloAI_StoryProxy:
    _parent: "HoloAI_Story"

    _api: HoloAI_API
    _story: Dict[str, Any]

    # story tree. As it doesn't exist on the backend, it won't be saved
    _tree: Dict[str, Any]

    banlists: List[BanList]
    biases: List[BiasGroup]
    model: Model
    preset: Preset
    prefix: str
    context_size: int

    def _handle_banlist(self, data: Dict[str, Any]) -> NoReturn:
        if "depressedWords" not in data:
            data["depressedWords"] = []

        ban_seq = data["depressedWords"]
        self.banlists = [BanList(*seq["value"], enabled = seq["enabled"]) for seq in ban_seq]

    def _handle_biasgroups(self, data: Dict[str, Any]) -> NoReturn:
        if "favoredPhrases" not in data:
            data["favoredPhrases"] = []

        self.biases = []
        for bias in data["favoredPhrases"]:
            self.biases.append(BiasGroup.from_data(bias))

    def _handle_preset(self, data: Dict[str, Any]) -> NoReturn:
        settings = data["genSettings"]

        self.preset = Preset.from_preset_data(settings)
        self.preset.name = "Preset"
        self.preset.model = self.model

    def __init__(self, parent: "HoloAI_Story", story: Dict[str, Any]):
        self._parent = parent

        self._api = parent._api
        self._story = story

        data = story["content"]["ct"]

        print(dumps(story, indent = 4))
        self._handle_banlist(data["depressedWords"])
        self._handle_biasgroups(data["favoredPhrases"])
        self._handle_preset(story)

        self._tree = {
            "fragments": [
                {
                    "prev": -1,
                    "next": [],
                    "origin": Story_DataFragmentOrigin.Prompt,
                    "content": data["content"] # replace <p></p> by \n ?
                }
            ],
            "path": [0],
            "position": 0,
        }

        # FIXME: variable context size ? From global settings ?
        self.context_size = 2048

        # TODO: remember (memory)
        # TODO: AN (authorsNote)

        # TODO: World Info (worldInfo)

    def _create_dataFragment(self, origin: Story_DataFragmentOrigin, content: str, **kwargs) -> NoReturn:
        fragments = self._tree["fragments"]

        path = self._tree["path"][:self._tree["position"]]

        current_index = path[-1]
        current_fragment = fragments[current_index]

        new_fragment = {
            "prev": current_index,
            "next": [],
            "origin": origin,
            "content": content
        }

        if origin is Story_DataFragmentOrigin.Edit:
            new_fragment["targets"] = kwargs.pop("targets")

        assert len(kwargs) == 0

        new_index = len(fragments)

        fragments.append(new_fragment)
        current_fragment["next"].append(new_index)

        path.append(new_index)
        self._tree["path"] = path
        self._tree["position"] = len(path) - 1

    def get_current_tree(self) -> List[Tuple[int, Dict[str, Any]]]:
        fragments = self._tree["fragments"]
        path = self._tree["path"][:self._tree["position"] + 1]

        return [(i, fragments[i]) for i in path]

    def __str__(self) -> str:
        current_tree = self.get_current_tree()

        content = {}
        for i, fragment in current_tree:
            if fragment["origin"] == Story_DataFragmentOrigin.Edit:
                targets = fragment["targets"]
                content[targets[0]] = fragment["content"]

                for target in targets[1:]:
                    content[target] = ""

            else:
                content[i] = fragment["content"]

        return "".join(*content.items())

    def build_context(self) -> List[int]:
        tokens = []

        # TODO: Remember tokens
        # TODO: AN tokens

        # TODO: optimize for large stories ?
        # edit is a pain for input in token form, so we use it's string representation instead
        story_content = str(self)
        story_content_size = self.context_size

        # TODO: add option to remove superfluous spaces at the end

        # only tokenize the tail to handle large stories
        story_tokens = []
        while len(story_tokens) < self.context_size:
            story_content_size *= 2
            story_tokens = Tokenizer.encode(self.model, story_content[-story_content_size:])

            # whole story content is tokenized
            if len(story_content) < story_content_size:
                break

        story_tokens = story_tokens[-self.context_size:]

        # TODO: LB tokens

        # TODO: Order and cut everything to fit

        tokens.extend(story_tokens)

        # Internal assert, should never happen
        assert len(tokens) <= self.context_size

        return tokens

    async def generate(self) -> "HoloAI_StoryProxy":
        input = self.build_context()
        rsp = await self._api.low_level.draw_completions(self.prefix, input, self.model, self.module)

        # FIXME: choose if 2 completions
        output = rsp["completions"]

        self._create_dataFragment(Story_DataFragmentOrigin.AI, output)

    def edit(self, start: int, end: int, replace: str) -> bool:
        l = 0
        fragments = self._tree["fragments"]

        targets = []

        for i in self._tree["path"]:
            fragment = fragments[i]
            content = fragment["content"]

            h = l + len(content)

            # detect beginning
            if l <= start < h:
                replace = content[:(start - l)] + replace

            # fragment inside edit
            if start < h:
                targets.append(i)

            # detect end
            if l <= end < h:
                replace = replace + content[(h - end):]
                break

        if len(targets) == 0:
            return False

        self._create_dataFragment(Story_DataFragmentOrigin.Edit, content, targets = targets)

        return True

    def undo(self) -> bool:
        if self._tree["position"] == 0:
            return False

        self._tree["position"] -= 1

        return True

    def redo(self) -> bool:
        if self._tree["position"] + 1 == len(self._tree["path"]):
            return False

        self._tree["position"] += 1

        return True

    async def save(self) -> bool:
        raise NotImplementedError()

    def choose(self, index: int) -> bool:
        path = self._tree["path"][:self._tree["position"] + 1]
        fragment = self._tree["fragments"][path[-1]]

        next = fragment["next"]
        if len(next) <= index:
            return False

        path.append(next[index])
        self._tree["path"] = path

        return True

    def flatten(self) -> NoReturn:
        raise NotImplementedError()

    async def delete(self):
        pass

class HoloAI_Story:
    _story_instances: Dict[str, HoloAI_StoryProxy]

    _api: HoloAI_API
#    _idstore: Idstore

    global_settings: GlobalSettings

    def __init__(self, api: HoloAI_API, global_settings: GlobalSettings):
        self._api = api
#        self._idstore = Idstore()

        self.global_settings = global_settings

        self._story_instances = {}

    def __iter__(self) -> Iterator[HoloAI_StoryProxy]:
        return self._story_instances.__iter__()

    def __getitem__(self, story_id: str) -> HoloAI_StoryProxy:
        return self._story_instances[story_id]

    def __len__(self) -> int:
        return len(self._story_instances)

    def load(self, story: Dict[str, Any]) -> HoloAI_StoryProxy:
        """
        Load a story proxy from a story object
        """
        story_id = story["id"]

        proxy = HoloAI_StoryProxy(self, story)
        self._story_instances[story_id] = proxy

        return proxy

    def loads(self, stories: Iterable[Dict[str, Any]]) -> List[HoloAI_StoryProxy]:
        loaded = []

        for story in stories:
            if story.get("decrypted"):
                proxy = self.load(story)
                loaded.append(proxy)

        return loaded

    async def load_from_remote(self) -> List[HoloAI_StoryProxy]:
        stories = await self._api.high_level.get_stories()

        return self.loads(stories)

    def create(self) -> HoloAI_StoryProxy:
        raise NotImplementedError()

    def select(self, story_id: str) -> Optional[HoloAI_StoryProxy]:
        """
        Select a story proxy from the previously created/loaded ones

        :param story_id: Id of the selected story

        :return: Story or None if the story does't exist in the handler
        """

        if story_id not in self._story_instances:
            return None

        return self._story_instances[story_id]

    def unload(self, story_id: str) -> NoReturn:
        """
        Unload a previously created/loaded story, free'ing the HoloAI_StoryProxy object
        """

        if story_id in self._story_instances:
            del self._story_instances[story_id]