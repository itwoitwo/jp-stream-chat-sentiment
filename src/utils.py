from yt_dlp import YoutubeDL
from pathlib import Path
import json
import pandas as pd
import csv


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
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(f"# attrs: {json.dumps(metadata, ensure_ascii=False)}\n")
            df.to_csv(f, index=False, quoting=csv.QUOTE_ALL, escapechar='\\', quotechar='"', encoding='utf-8')
        return True
    except (IOError, json.JSONDecodeError, Exception):
        return False


