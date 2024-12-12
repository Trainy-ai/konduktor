import enum


class Storage(object):
    pass

class StorageMode(enum.Enum):

    COPY = enum.auto()

class StoreType(enum.Enum):
    """Enum for different types of stores
    """
    GCS = 'GCS'