from yt_dlp import YoutubeDL
from pathlib import Path
import json
import pandas as pd
import csv
import os
import io
import requests
import time
import traceback
from PySide6.QtCore import QThread, Signal
from urllib.parse import urlparse
import torch
from torch.utils.data import DataLoader
from datasets import Dataset
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from constants import ErrorCode, ERROR_MESSAGE, EMOTION_NAMES, CHECKPOINT


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
                self.process_step('ダウンロードの準備中')
                if 'youtube' in parsed_url.netloc:
                    df, metadata = self.download_youtube_chats()
                elif 'twitch' in parsed_url.netloc:
                    video_id = parsed_url.path.split('/')[-1]
                    df, metadata = download_twitch_chats(video_id, self.save_path)
                else:
                    raise ProcessError('YoutubeかTwitchのURLを入力してください')

            if not self.skip_analyze:
                df['emotion'] = self.classify_emotions(
                    df['chat'].tolist(), self.batch_size, self.token_size, self.device
                )
                save_dataframe_with_metadata(self.save_path, metadata, df)
            self.store.set_data({'df': df, 'metadata': metadata})
            self.process_step('Complete!!')
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
        self.process_step('csvファイルへの変換中')
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

    def process_step(self, step_name):
        self.step_name.emit(step_name)
        if self.isInterruptionRequested():
            raise ProcessError(ERROR_MESSAGE['CANCEL'], ErrorCode['CANCEL'])

    def classify_emotions(self, texts, batch_size, token_size, device):
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
                self.process_step('感情分析の実行中...')
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


def download_twitch_chats(video_id, output_path):
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

    df = pd.DataFrame({'chat': chats, 'second': seconds, 'minute': minutes})
    df.to_csv(output_path, index=False, quoting=csv.QUOTE_ALL, escapechar='\\', quotechar='"', encoding='utf-8')
    return df, {'url': f"https://www.twitch.tv/videos/{video_id}"}


class Store:
    def __init__(self):
        self._data = None

    def set_data(self, data):
        self._data = data

    def get_data(self):
        return self._data
