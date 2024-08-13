from enum import Enum, auto
from types import SimpleNamespace


class ErrorCode(Enum):
    UNKNOWN = auto()
    CANCEL = auto()


ERROR_MESSAGE = {
    'CANCEL': 'キャンセルされました'
}

EMOTION_NAMES = ('喜び', '悲しみ', '期待', '驚き', '怒り', '恐れ', '嫌悪', '信頼')

CHECKPOINT = {
    'TOKENIZER': 'cl-tohoku/bert-base-japanese-whole-word-masking',
    'MODEL': 'my_model/'
}
