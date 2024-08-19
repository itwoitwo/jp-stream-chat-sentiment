from enum import Enum, auto


class ErrorCode(Enum):
    UNKNOWN = auto()
    CANCEL = auto()


ERROR_MESSAGE = {
    'CANCEL': 'キャンセルされました'
}

EMOTION_NAMES = ('喜び', '悲しみ', '期待', '驚き', '怒り', '恐れ', '嫌悪', '信頼', '中立')

EMOTION_COLORS = {
    '喜び': '#FFD700',    # ゴールド（黄金色）
    '期待': '#FFA07A',    # ライトサーモン
    '信頼': '#90EE90',    # ライトグリーン
    '驚き': '#00CED1',    # ダークターコイズ
    '悲しみ': '#6495ED',  # コーンフラワーブルー
    '恐れ': '#4682B4',    # スティールブルー
    '嫌悪': '#8B008B',    # ダークマゼンタ
    '怒り': '#CD5C5C',    # インディアンレッド
    '中立': 'grey'
}

CHECKPOINT = {
    'TOKENIZER': 'cl-tohoku/bert-base-japanese-whole-word-masking',
    'MODEL': 'my_model/'
}

STEP_LABEL = {
    'MODEL_LOADING': 'モデルをロード中...',
    'MODEL_LOADED': 'モデルのロードが完了しました',
    'DOWNLOAD_PREPARE': 'ダウンロードの準備中',
    'DOWNLOADING': 'チャットのダウンロード中...',
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
