from enum import Enum, auto
from types import SimpleNamespace


class ErrorCode(Enum):
    UNKNOWN = auto()
    CANCEL = auto()


ERROR_MESSAGE = {
    'CANCEL': 'キャンセルされました'
}