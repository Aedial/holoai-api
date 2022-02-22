from copy import deepcopy

from holoai_api.BiasGroup import BiasGroup
from holoai_api.Preset import Model
from holoai_api.Tokenizer import Tokenizer

from typing import Dict, Any, Optional

class GlobalSettings:
    _DEFAULT_SETTINGS = {
    }

    _settings: Dict[str, Any]

    def __init__(self, **kwargs):
        self._settings = {}

        for setting in self._DEFAULT_SETTINGS:
            self._settings[setting] = kwargs.pop(setting, self._DEFAULT_SETTINGS[setting])

        assert len(kwargs) == 0, f"Invalid global setting name: {', '.join(kwargs)}"

    def __setitem__(self, o: str, v: Any) -> None:
        assert o in self._settings, f"Invalid setting: {o}"

        self._settings[o] = v

    def __getitem__(self, o: str) -> Any:
        assert o in self._settings, f"Invalid setting: {o}"

        return self._settings[o]

    def to_settings(self, model: Model) -> Dict[str, Any]:
        settings = {
        }

        tokenizer_name = Tokenizer.get_tokenizer_name(model)

        return settings