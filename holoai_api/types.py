from enum import Enum, auto, EnumMeta
from json import dumps

from typing import Union, Dict, List, Optional, Any

class StrEnum(str, Enum):
    pass

# FIXME: get proper names
class Model(StrEnum):
    Model_6B = "gpt-j-6b-2-7"
    Model_13B = "fs-model-0-1"

_DEFAULT_PREFIX_FIELDS = {
    "location": 0,
    "category": None,
    "tags": None,
}

class Prefix(Enum):
    Novel = { "prefix_name": "googreads" }
    Fanfic = { "prefix_name": "ao3" }
    Romance = { "prefix_name": "literotica" }
#    CYOA = { "prefix_name": "cyoa" }
    Generic = { }

    def to_prefix_header(self, metadata: Dict[str, Any],
                               local_overwrite: Optional[Dict[str, Any]] = None) -> Union[str, List[int]]:
        assert type(metadata) is dict, f"Expected type 'dict' for metadata, but got type '{type(metadata)}'"
        assert local_overwrite is None or type(local_overwrite) is dict, f"Expected None or type 'dict' for local_overwrite, but got type '{type(local_overwrite)}'"

        prefix = { "source": self.value.get("prefix_name") }

        for field in _DEFAULT_PREFIX_FIELDS:
            if local_overwrite is not None and field in local_overwrite:
                prefix[field] = local_overwrite[field]
            elif field in metadata:
                prefix[field] = metadata[field]
            else:
                prefix[field] = _DEFAULT_PREFIX_FIELDS[field]

        # drop the None vqlues (fields not set)
        prefix = { field: value for field, value in prefix.items() if value is not None }
        prefix = dumps(prefix, separators = (',', ':'))

        return prefix

class Order_by(Enum):
    Creation_date = "creation_date"

class Listing(Enum):
    Private = auto()
    Unlisted = auto()
    Public = auto()