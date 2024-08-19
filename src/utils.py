import csv
import io
import json
import os
import time
import traceback
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import requests
import torch
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import QLabel, QLineEdit, QPushButton, QGraphicsDropShadowEffect
from PySide6.QtGui import QColor, QFont
from datasets import Dataset
from torch.utils.data import DataLoader
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from yt_dlp import YoutubeDL

from constants import ErrorCode, ERROR_MESSAGE, EMOTION_NAMES, CHECKPOINT, STEP_LABEL


def download_chats(url, path, hook):
    output_path = str(Path(path) / '%(id)s')

    with (YoutubeDL({
        'format': 'best',
        'outtmpl': output_path,
        'writesubtitles': True,
        'skip_download': True,
        'noprogress': True,
        'progress_hooks': [hook]
    }) as ydl):
        res = ydl.extract_info(url, download=False)
        ydl.download([url])

    return res


def json_to_df(path):
    chats = []
    timestamps = []
    minutes = []

    with open(path, 'r', encoding='utf-8') as file:
        for line in file:
            if line.strip() == '':
                continue
            l_json = json.loads(line)
            j_action = l_json['replayChatItemAction']['actions'][0]
            if 'addChatItemAction' in j_action:
                item = j_action['addChatItemAction']['item']
                if 'liveChatTextMessageRenderer' in item:
                    message_runs = item['liveChatTextMessageRenderer']['message']['runs']
                    if message_runs and 'text' in message_runs[0]:
                        chat = message_runs[0]['text']
                        timestamp = int(l_json['replayChatItemAction']['videoOffsetTimeMsec']) // 1000
                        chats.append(chat)
                        timestamps.append(timestamp)
                        minutes.append(int(timestamp // 60))

    return pd.DataFrame({'chat': chats, 'second': timestamps, 'minute': minutes})


def save_dataframe_with_metadata(path, metadata, df):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(f"# attrs: {json.dumps(metadata, ensure_ascii=False)}\n")
        df.to_csv(f, index=False, quoting=csv.QUOTE_ALL, escapechar='\\', quotechar='"', encoding='utf-8')


class ProcessError(Exception):
    def __init__(self, message='', code=ErrorCode['UNKNOWN']):
        self.message = message
        self.code = code

    def __str__(self):
        return self.message


class Worker(QThread):
    step_name = Signal(str)
    progress = Signal(int)
    error = Signal(str)
    finished = Signal()

    def __init__(self, save_path, url, skip_analyze, force_cpu, batch_size, token_size, nlp_components, store):
        super().__init__()
        self.save_path = save_path
        self.url = url
        self.skip_analyze = skip_analyze
        self.tokenizer = nlp_components['tokenizer']
        self.model = nlp_components['model']
        self.batch_size = batch_size
        self.token_size = token_size
        if force_cpu:
            self.device = torch.device('cpu')
        else:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        self.store = store

        self.skip_download = os.path.exists(save_path)

    def run(self):
        try:
            parsed_url = urlparse(self.url)
            if self.skip_download:
                df, metadata = read_csv_with_metadata(self.save_path)
            else:
                self.process_step(STEP_LABEL['DOWNLOAD_PREPARE'])
                if 'youtube' in parsed_url.netloc:
                    df, metadata = self.download_youtube_chats()
                elif 'twitch' in parsed_url.netloc:
                    video_id = parsed_url.path.split('/')[-1]
                    df, metadata = self.download_twitch_chats(video_id)
                else:
                    raise ProcessError('YoutubeかTwitchのURLを入力してください')

            if not self.skip_analyze:
                df['emotion'] = self.classify_emotions(
                    df['chat'].tolist(), self.batch_size, self.token_size, self.device
                )
                save_dataframe_with_metadata(self.save_path, metadata, df)
            self.store.set_data({'df': df, 'metadata': metadata})
            self.process_step(STEP_LABEL['COMPLETE'])
            self.progress.emit(100)
        except Exception as e:
            error_msg = f'エラーが発生しました: {str(e)}\n\n{traceback.format_exc()}'
            if isinstance(e, ProcessError):
                if e.code == ErrorCode['CANCEL']:
                    error_msg = ERROR_MESSAGE['CANCEL']
            self.error.emit(error_msg)

    def download_youtube_chats(self):
        directory = os.path.dirname(self.save_path)
        res = download_chats(self.url, directory, self.yt_dlp_hook)
        self.process_step(STEP_LABEL['CONVERTING_CSV'])
        title = res['title']
        video_id = res['id']
        timestamp = pd.to_datetime(res['timestamp'], unit='s', utc=True)

        json_path = f"{directory}/{video_id}.live_chat.json"
        df = json_to_df(json_path)

        metadata = {
            'title': title,
            'upload_at': timestamp.tz_convert('Asia/Tokyo').strftime("%Y/%m/%d/%H:%M"),
            'url': self.url,
        }
        save_dataframe_with_metadata(self.save_path, metadata, df)
        os.remove(json_path)
        return df, metadata

    def yt_dlp_hook(self, d):
        if self.isInterruptionRequested():
            raise ProcessError(ERROR_MESSAGE['CANCEL'], ErrorCode['CANCEL'])
        if d['status'] == 'downloading':
            self.step_name.emit(f"チャットのダウンロード中: {d['_default_template']}")

    def download_twitch_chats(self, video_id):
        self.process_step(STEP_LABEL['DOWNLOAD_PREPARE'])
        api_url = 'https://gql.twitch.tv/gql'
        first_data = json.dumps([
            {
                "operationName": "VideoCommentsByOffsetOrCursor",
                "variables": {
                    "videoID": video_id,
                    "contentOffsetSeconds": 0
                },
                "extensions": {
                    "persistedQuery": {
                        "version": 1,
                        "sha256Hash": "b70a3591ff0f4e0313d126c6a1502d79a1c02baebb288227c582044aa76adf6a"
                    }
                }
            }
        ])

        # 1回目のセッションスタート
        session = requests.Session()
        session.headers = {'Client-ID': 'kd1unb4b3q4t58fwlpcbzcbnm76a8fp', 'content-type': 'application/json'}

        response = session.post(
            api_url,
            first_data,
            timeout=10
        )

        response.raise_for_status()
        data = response.json()

        self.process_step(STEP_LABEL['DOWNLOADING'])

        chats = []
        seconds = []
        minutes = []
        for comment in data[0]['data']['video']['comments']['edges']:
            chats.append(comment['node']['message']['fragments'][0]['text'])
            timestamp = int(comment['node']['contentOffsetSeconds'])
            seconds.append(timestamp)
            minutes.append(timestamp // 60)

        cursor = None
        if data[0]['data']['video']['comments']['pageInfo']['hasNextPage']:
            cursor = data[0]['data']['video']['comments']['edges'][-1]['cursor']
            time.sleep(0.1)

        # session loop
        while cursor:
            self.process_step(STEP_LABEL['DOWNLOADING'])
            response = session.post(
                api_url,
                get_json_data(video_id, cursor),
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            for comment in data[0]['data']['video']['comments']['edges']:
                chats.append(comment['node']['message']['fragments'][0]['text'])
                timestamp = int(comment['node']['contentOffsetSeconds'])
                seconds.append(timestamp)
                minutes.append(timestamp // 60)

            if data[0]['data']['video']['comments']['pageInfo']['hasNextPage']:
                cursor = data[0]['data']['video']['comments']['edges'][-1]['cursor']
                time.sleep(0.1)
            else:
                cursor = None

        metadata = {'url': f"https://www.twitch.tv/videos/{video_id}"}
        df = pd.DataFrame({'chat': chats, 'second': seconds, 'minute': minutes})
        save_dataframe_with_metadata(self.save_path, metadata, df)
        return df, metadata

    def process_step(self, step_name):
        self.step_name.emit(step_name)
        if self.isInterruptionRequested():
            raise ProcessError(ERROR_MESSAGE['CANCEL'], ErrorCode['CANCEL'])

    def classify_emotions(self, texts, batch_size, token_size, device):
        self.process_step(STEP_LABEL['EMOTION_ANALYZE_PREPARE'])
        self.model.to(device)
        dataset = Dataset.from_dict({'text': texts})
        dataset = dataset.map(
            lambda x: self.tokenizer(x['text'], truncation=True, padding='max_length', max_length=token_size),
            batched=True)
        dataset.set_format(type='torch', columns=['input_ids', 'attention_mask'])
        dataloader = DataLoader(dataset, batch_size=batch_size)

        results = []
        self.model.eval()
        total_batches = len(dataloader)
        with torch.no_grad():
            for batch_idx, batch in enumerate(dataloader):
                self.process_step(STEP_LABEL['EMOTION_ANALYZING'])
                batch = {k: v.to(device) for k, v in batch.items()}
                outputs = self.model(**batch)
                predictions = torch.argmax(outputs.logits, dim=-1)
                results.extend([self.model.config.id2label[pred.item()] for pred in predictions])

                progress = (batch_idx + 1) / total_batches * 100
                self.progress.emit(progress)
        return results


def read_csv_with_metadata(file_path):
    metadata = {}
    with open(file_path, 'r', encoding='utf-8') as file:
        first_line = file.readline().strip()
        if first_line.startswith('# attrs:'):
            metadata = json.loads(first_line[8:])
            csv_data = file.readlines()
        else:
            file.seek(0)
            csv_data = file.readlines()

    df = pd.read_csv(io.StringIO(''.join(csv_data)), quotechar='"')

    return df, metadata


class ModelLoader(QThread):
    finished = Signal(object)

    def run(self):
        num_labels = len(EMOTION_NAMES)
        label2id = {label: i for i, label in enumerate(EMOTION_NAMES)}
        id2label = {i: label for i, label in enumerate(EMOTION_NAMES)}

        model = AutoModelForSequenceClassification.from_pretrained(CHECKPOINT['MODEL'], num_labels=num_labels)
        model.config.id2label = id2label
        model.config.label2id = label2id

        tokenizer = AutoTokenizer.from_pretrained(CHECKPOINT['TOKENIZER'], clean_up_tokenization_spaces=True)
        self.finished.emit({'tokenizer': tokenizer, 'model': model})


def get_json_data(video_id, cursor):
    loop_data = json.dumps([
        {
            "operationName": "VideoCommentsByOffsetOrCursor",
            "variables": {
                "videoID": video_id,
                "cursor": cursor
            },
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "b70a3591ff0f4e0313d126c6a1502d79a1c02baebb288227c582044aa76adf6a"
                }
            }
        }
    ])
    return loop_data


class Store:
    def __init__(self):
        self._data = None

    def set_data(self, data):
        self._data = data

    def get_data(self):
        return self._data


class ClickableLabel(QLabel):
    clicked = Signal()  # クリックされたときに発行するシグナルを定義

    def __init__(self, text):
        super().__init__(text)
        self.setStyleSheet("""
            ClickableLabel {
                font-size: 20px;
                border: 2px dashed #888888;
                border-radius: 10px;
                padding: 10px;
                background-color: #f0f0f0;
            }
            ClickableLabel:hover {
                background-color: #e0e0e0;
                border-color: #666666;
                cursor: pointer;  /* マウスカーソルを手の形に変更 */
            }
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class ClickableLineEdit(QLineEdit):
    def __init__(self, on_click):
        super().__init__()
        self.on_click = on_click

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.on_click()
        super().mousePressEvent(event)


class StyledButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setup_ui()

    def setup_ui(self):
        self.setMinimumHeight(50)
        self.setMinimumWidth(200)

        # フォントの設定
        font = QFont()
        font.setFamily('Meiryo')  # 日本語フォント
        font.setPointSize(12)
        font.setBold(True)
        self.setFont(font)

        # ドロップシャドウ効果の追加
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 5)
        self.setGraphicsEffect(shadow)

        self.update_style()

    def update_style(self):
        if self.text() == 'Start':
            bg_color = '#4CAF50'  # 緑色
            hover_color = '#45a049'
            pressed_color = "#3e8e41"
        else:
            bg_color = '#F44336'  # 赤色
            hover_color = '#D32F2F'
            pressed_color = '#C62828'

        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                color: white;
                border: none;
                border-radius: 25px;
                font-size: 16px;
                font-weight: bold;
                padding: 10px 20px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:pressed {{
                background-color: {pressed_color};
            }}
            QPushButton:disabled {{
                background-color: #BDBDBD;
                color: #757575;
            }}
        """)

    def setText(self, text):
        super().setText(text)
        self.update_style()

    def setEnabled(self, enabled):
        super().setEnabled(enabled)
        self.update_style()
