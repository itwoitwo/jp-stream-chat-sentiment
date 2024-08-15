from yt_dlp import YoutubeDL
from pathlib import Path
import json
import pandas as pd
import csv
import os
import io
import traceback
from PySide6.QtCore import QThread, Signal
from urllib.parse import urlparse, parse_qs
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
                        timestamp = int(l_json['replayChatItemAction']['videoOffsetTimeMsec']) / 1000
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

    def __init__(self, directory, url, force_cpu, batch_size, token_size, nlp_components):
        super().__init__()
        self.directory = directory
        self.url = url
        self.tokenizer = nlp_components['tokenizer']
        self.model = nlp_components['model']
        self.batch_size = batch_size
        self.token_size = token_size
        if force_cpu:
            self.device = torch.device('cpu')
        else:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    def run(self):
        try:
            parsed_url = urlparse(self.url)
            query_params = parse_qs(parsed_url.query)
            output_path = f"{self.directory}/{query_params['v'][0]}.csv"
            if not os.path.exists(output_path):
                self.process_step('ダウンロードの準備中')
                res = download_chats(self.url, self.directory, self.yt_dlp_hook)
                self.process_step('csvファイルへの変換中')
                title = res['title']
                video_id = res['id']
                timestamp = pd.to_datetime(res['timestamp'], unit='s', utc=True)

                json_path = f"{self.directory}/{video_id}.live_chat.json"
                df = json_to_df(json_path)

                metadata = {
                    'title': title,
                    'upload_at': timestamp.tz_convert('Asia/Tokyo').strftime("%Y/%m/%d/%H:%M"),
                    'url': self.url,
                    'id': video_id
                }
                save_dataframe_with_metadata(output_path, metadata, df)
                os.remove(json_path)
            else:
                df, metadata = read_csv_with_metadata(output_path)

            df['emotion'] = self.classify_emotions(df['chat'].tolist(), self.batch_size, self.token_size, self.device)
            save_dataframe_with_metadata(output_path, metadata, df)
            self.process_step('Complete!!')
            self.progress.emit(100)
        except Exception as e:
            error_msg = f'エラーが発生しました: {str(e)}\n\n{traceback.format_exc()}'
            if isinstance(e, ProcessError):
                if e.code == ErrorCode['CANCEL']:
                    error_msg = ERROR_MESSAGE['CANCEL']
            self.error.emit(error_msg)

    def yt_dlp_hook(self, d):
        if self.isInterruptionRequested():
            raise ProcessError(ERROR_MESSAGE['CANCEL'], ErrorCode['CANCEL'])
        if d['status'] == 'downloading':
            self.step_name.emit(f"チャットのダウンロード中: {d['_default_template']}")

    def process_step(self, step_name):
        self.step_name.emit(step_name)
        if self.isInterruptionRequested():
            raise ProcessError(ERROR_MESSAGE['CANCEL'], ErrorCode['CANCEL'])

        if step_name == 'Downloading data':
            if 'error' in self.url.lower():
                raise ProcessError('Failed to download data from the provided URL.')
        elif step_name == 'Processing data':
            if not os.path.exists(self.directory):
                raise ProcessError(f'Directory not found: {self.directory}')

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
