from enum import Enum, auto

class StrEnum(str, Enum):
    pass

# FIXME: get proper names
class Model(StrEnum):
    Model_6B = "model-2-7"

class Prefix(Enum):
    Novel = { "prefix_name": "googreads", "tokens": [ 4895, 10459, 2404, 11274, 40779, 2430, 24886, 1298, 15, 92 ] }
    Fanfic = { "prefix_name": "ao3", "tokens": [4895, 10459, 2404, 5488, 18, 2430, 24886, 1298, 15, 92 ] }
    Romance = { "prefix_name": "literotica", "tokens": [ 4895, 10459, 2404, 17201, 313, 3970, 2430, 24886, 1298, 15, 553, 22872, 2404, 37, 316, 680, 20662 ] }
#    CYOA = { "prefix_name": "cyoa" }
    Generic = { "prefix_name": "", "tokens": [ 4895, 24886, 1298, 15, 92 ] }

class Order_by(Enum):
    Creation_date = "creation_date"

class Listing(Enum):
    Private = auto()
    Unlisted = auto()
    Public = auto()