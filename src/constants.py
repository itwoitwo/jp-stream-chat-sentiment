from enum import Enum, auto


class ErrorCode(Enum):
    UNKNOWN = auto()
    CANCEL = auto()


ERROR_MESSAGE = {
    'CANCEL': 'キャンセルされました'
}

EMOTION_NAMES = ('喜び', '悲しみ', '期待', '驚き', '怒り', '恐れ', '嫌悪', '信頼')

EMOTION_COLORS = {
    '喜び': 'orange',
    '嫌悪': 'black',
    '怒り': 'red',
    '恐れ': 'blue',
    '悲しみ': 'lightblue',
    '期待': 'yellow',
    '驚き': 'green',
}

CHECKPOINT = {
    'TOKENIZER': 'cl-tohoku/bert-base-japanese-whole-word-masking',
    'MODEL': 'my_model/'
}

STEP_LABEL = {
    'MODEL_LOADING': 'モデルをロード中...',
    'MODEL_LOADED': 'モデルのロードが完了しました',
    'DOWNLOAD_PREPARE': 'ダウンロードの準備中',
    'COMPLETE': '完了！',
    'CONVERTING_CSV': 'csvファイルへの変換中',
    'EMOTION_ANALYZING': '感情分析の実行中...'
}

BUTTON_LABEL = {
    'START': 'Start',
    'LOADING': 'Now Loading...',
    'CANCEL': 'キャンセル',
    'CANCELING': 'キャンセル中...',
}
