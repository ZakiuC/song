import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
import json
import os
import argparse
import time
import sys
import pyperclip
from fake_useragent import UserAgent
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import re

def get_session():
    """
    创建一个会话，配置重试策略和随机用户代理。
    返回一个配置好的requests.Session对象。
    """
    session = requests.Session()
    retry = Retry(connect=3, backoff_factor=0.5)  # 定义连接重试策略：最多重试3次，指数退避因子为0.5
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    session.headers = {'User-Agent': UserAgent().random}  # 配置随机用户代理
    return session

def extract_songs_and_title(input_text):
    """
    从提供的文本中提取专辑标题和歌曲列表。
    文本应该包括专辑名称、空行、然后是歌曲标题和链接。
    返回专辑标题和歌曲信息列表（包括歌曲标题和链接）。
    """
    lines = input_text.strip().split('\n')
    
    if not lines or not lines[0].startswith("《") or not lines[1].strip() == "":
        print("错误：第一行不是有效的专辑名")
        return "未知专辑", []
    
    title = lines[0].strip()
    
    songs = []
    base_title = None
    tune = None

    for i in range(2, len(lines)):  # 从第三行开始解析歌曲信息
        line = lines[i].strip()
        
        # 查找歌曲基本信息
        song_match = re.match(r"【\d+\.?\s*(.*?)】", line)
        if song_match:
            base_title = song_match.group(1).strip()
            tune = None  # 重置调式信息
            continue
        
        # 查找调式描述
        tune_match = re.search(r"(.*?)(原调)?调", line)
        if tune_match:
            tune_note = tune_match.group(1)
            is_yuandiao = "原调" in line
            tune = f"{tune_note}调" if is_yuandiao else f"{tune_note}调"
            tune = re.sub(r"（|）", "", tune)
            continue
        
        # 查找链接
        url_match = re.match(r"https?://\S+", line)
        if url_match and base_title:
            full_title = f"{base_title} | {tune}" if tune else base_title
            songs.append({'title': full_title, 'url': url_match.group(0)})

    return title, songs

def save_as_json(songs, directory, filename):
    """
    将提取的歌曲信息保存为JSON格式。
    参数：
    - songs: 歌曲信息列表。
    - directory: 保存JSON文件的目录。
    - filename: JSON文件的名称。
    """
    if not os.path.exists(directory):
        os.makedirs(directory)
    file_path = os.path.join(directory, filename)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(songs, f, ensure_ascii=False, indent=4)
    return file_path

def download_music(song, directory, session):
    """
    下载单个歌曲。
    参数：
    - song: 包含歌曲标题和链接的字典。
    - directory: 保存下载的音乐的目录。
    - session: 用于请求的会话对象。
    """
    song_title = song['title']
    url = song['url']
    safe_song_title = song_title.replace("|", " -").replace("?", "").replace(":", "").replace("\"", "").replace("<", "").replace(">", "").replace("*", "")
    
    try:
        response = session.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        sources = soup.find_all('source')
        if not sources:
            print(f"没有找到音频源：{safe_song_title}.")
            return
        for source in sources:
            music_url = source['src'].replace('×tamp=', '&timestamp=')
            if "id=" in music_url and "timestamp=" in music_url and "code=" in music_url:
                print(f"下载：{safe_song_title}")
                music_response = session.get(music_url, stream=True)
                music_response.raise_for_status()
                total_size = int(music_response.headers.get('content-length', 0))
                progress_bar = tqdm(total=total_size, unit='iB', unit_scale=True)
                with open(os.path.join(directory, f"{safe_song_title}.mp3"), 'wb') as f:
                    for data in music_response.iter_content(1024):
                        progress_bar.update(len(data))
                        f.write(data)
                progress_bar.close()
                print(f"已下载：{safe_song_title}")
    except requests.exceptions.RequestException as e:
        print(f"下载错误 {safe_song_title}: {e}")

def main():
    """
    主函数，负责从剪贴板读取数据，解析，保存JSON，并下载音乐。
    """
    parser = argparse.ArgumentParser(description="从剪贴板提取信息并下载音乐文件")
    parser.add_argument('-t', '--readDir', type=str, default="target", help="包含音乐数据 JSON 文件的目录")
    parser.add_argument('-s', '--saveDir', type=str, default="music", help="保存音乐文件的目录")
    args = parser.parse_args()
    input_text = pyperclip.paste()
    album_title, songs = extract_songs_and_title(input_text)
    if not songs or album_title == "未知专辑":
        print("错误：未能从剪贴板内容中提取有效的歌曲信息和标题。")
        sys.exit(1)
    filename = f"{album_title}.json"
    saved_path = save_as_json(songs, args.readDir, filename)
    print(f"信息已保存至：{saved_path}")
    session = get_session()
    directory = os.path.join(args.saveDir, album_title)
    if not os.path.exists(directory):
        os.makedirs(directory)
    for song in songs:
        download_music(song, directory, session)
    print("所有文件都已下载完毕")

if __name__ == "__main__":
    main()
