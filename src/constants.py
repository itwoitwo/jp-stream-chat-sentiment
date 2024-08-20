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
    '中立': 'grey',
    '未分類': 'grey'
}

CHECKPOINT = {
    'TOKENIZER': 'tohoku-nlp/bert-base-japanese-v3',
    'MODEL': 'iton/YTLive-JaBERT-Emotion-v1'
}

STEP_LABEL = {
    'MODEL_LOADING': 'モデルをロード中...',
    'MODEL_LOADED': 'モデルのロードが完了しました',
    'DOWNLOAD_PREPARE': 'ダウンロードの準備中...',
    'DOWNLOADING': 'チャットのダウンロード中...',
    'COMPLETE': '完了！',
    'CONVERTING_CSV': 'csvファイルへの変換中...',
    'EMOTION_ANALYZE_PREPARE': '感情分析の準備中...',
    'EMOTION_ANALYZING': '感情分析の実行中...'
}

BUTTON_LABEL = {
    'START': 'Start',
    'LOADING': 'Now Loading...',
    'CANCEL': 'キャンセル',
    'CANCELING': 'キャンセル中...',
}

COMMON_STYLE = """
            QWidget {
                font-size: 16px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QMainWindow {
                background-color: #ffffff;
            }
            QCheckBox::indicator {
            width: 20px;
            height: 20px;
            }
            QTabWidget::pane { 
                border-top: 1px solid #ddd;
                top: -1px; 
            }
            QTabBar::tab {
                padding: 12px 0px;
                color: #777;
                border: 1px solid #ccc;
                border-bottom: none;
                background: #f0f0f0;
                min-width: 50%;
                margin-top: 0;
            }
            QTabBar::tab:selected {
                color: #333;
                background: #ffffff;
                border: 1px solid #ddd;
                border-bottom: 1px solid #ffffff;
                margin-top: 0;
            }
            QTabBar::tab:hover:!selected {
                background: #e0e0e0;
            }
            QTabWidget>QWidget>QWidget{
                background: #ffffff;
                border-top: 1px solid #ddd;
            }
            QSpinBox {
                padding-right: 15px;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 20px;
            }
        """
