from json import loads
from os import listdir
from os.path import join, abspath, dirname, exists
from copy import deepcopy
from random import choice

from holoai_api.types import Model

from typing import Dict, List, Any, Union, Optional, NoReturn

class Preset:
    _TYPE_MAPPING = {
        "id": str,
        "noCompletions": int,
        "numCharactersRequested": int,
        "repetitionPenalty": (int, float),
        "repetitionPenaltySlope": (int, float),
        "tfs": (int, float),
        "temperature": (int, float),
        "generateUntilSentence": bool,
    }

    _DEFAULT = {
        "noCompletions": 2,
        "numCharactersRequested": 200,
        "repetitionPenalty": 1.1,
        "repetitionPenaltySlope": 4.5,
        "tfs": 0.8,
        "temperature": 1.1,
        "generateUntilSentence": False,
    }

    _settings: Dict[str, Any]
    name: str
    model: Model

    def __init__(self, name: str, model: Model, settings: Optional[Dict[str, Any]] = None):
        self.name = name
        self.model = model

        self._settings = {}
        self.update(settings)

    def __setitem__(self, o: str, v: Any):
        assert o in self._TYPE_MAPPING, f"'{o}' is not a valid setting"
        assert isinstance(v, self._TYPE_MAPPING[o]), f"Expected type '{self._TYPE_MAPPING[o]}' for {o}, but got type '{type(v)}'"

        self._settings[o] = v

    def __contains__(self, o: str) -> bool:
        return o in self._settings

    def __getitem__(self, o: str) -> Optional[Any]:
        return self._settings.get(o)

    def __repr__(self) -> str:
        model = self.model.value if self.model is not None else "<?>"
        return f"Preset: '{self.name} ({model})'"

    def to_settings(self) -> Dict[str, Any]:
        settings = deepcopy(self._DEFAULT)
        settings.update(self._settings)

        if "id" in settings:
            del settings["id"]

        return settings

    def to_file(self, path: str) -> NoReturn:
        raise NotImplementedError()

    def copy(self) -> "Preset":
        return Preset(self.name, self.model, deepcopy(self._settings))

    def set(self, name: str, value: Any) -> "Preset":
        self[name] = value

        return self

    def update(self, values: Dict[str, Any]) -> "Preset":
        for k, v in values.items():
            self[k] = v

        return self

    @classmethod
    def from_preset_data(cls, settings: Dict[str, Any]) -> "Preset":
        name = "???"
        model = None

        settings.pop("badWords", None)     # get rid of duplicate option
        settings.pop("logitBias", None)    # get rid of cuplicate option

        c = cls(name, model, settings)

        return c

    @classmethod
    def from_file(cls, path: str) -> "Preset":
        with open(path) as f:
            data = loads(f.read())

        return cls.from_preset_data(data)