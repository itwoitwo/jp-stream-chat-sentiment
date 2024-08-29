# jp-stream-chat-sentiment

## 概要
Youtube、Twitchのライブストリームのアーカイブからチャットをダウンロードし、深層学習モデルを用いた感情分析を行います。
感情分析を行った結果は操作可能なグラフで表示し、ライブストリームがどの時間帯で盛り上がっていたか、どのような感情が支配的であったか等を視覚的に確認することができます。

## 特徴
- チャットのダウンロード機能、時間帯毎のコメント数の表示機能
- [東北大学の日本語BERT](https://github.com/cl-tohoku/bert-japanese)をファインチューニングした[モデル](https://huggingface.co/iton/YTLive-JaBERT-Emotion-v1)による感情分析
- Pyside6とplotlyによるGUI操作を実現
- 単体でGoogle Colabで動作可能なファイルを同梱

## 始め方

### 必要条件

```
Python 3.8以上 (3.12で動作確認済)
cuda 12.1以上 (GPUによる推論を行う場合のみ)
```

### Google Colab
`for_google_colab.ipynb`をダウンロードし、Google Colab上で実行してください。

### インストール(ローカルPCで動作させたい場合)
1. リポジトリをクローンします：
   ```
   $ git clone https://github.com/itwoitwo/jp-stream-chat-sentiment.git
   $ cd jp-stream-chat-sentiment
   ```

2. 仮想環境を作成し、アクティベートします：
   ```
   $ python -m venv venv
   $ source venv/bin/activate  # Linuxまたは macOS
   # または
   $ venv\Scripts\activate  # Windows
   ```

3. 必要なパッケージをインストールします：
   ```
   $ pip install -r requirements.txt
   ```

4. 実行
    ```
    $ python src/main.py
    ```

## 注意事項
* Youtube、TwitchのAPI仕様が変更された場合使用できなくなる場合があります。
* Youtubeの場合は内部で[yt-dlp](https://github.com/yt-dlp/yt-dlp)を使用しているため、`$ pip install -U yt-dlp`で動作するかもしれません。

## 免責事項
本プロジェクトのチャットダウンロード方法は、YouTube及びTwitchの公式が推奨している方法ではありません。これらのプラットフォームの利用規約に違反する可能性があります。本ツールの使用は自己責任で行ってください。開発者は、本ツールの使用によって生じたいかなる損害や法的問題に対しても責任を負いません。

## ライセンス
ご自由にお使いください。