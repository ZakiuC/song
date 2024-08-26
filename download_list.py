import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
import json
import os
import argparse
from fake_useragent import UserAgent
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def get_session():
    """
    创建一个会话，配置重试策略和随机用户代理。
    返回一个配置好的requests.Session对象。
    """
    session = requests.Session()
    retry = Retry(connect=3, backoff_factor=0.5)  # 重试策略，最多重试3次，指数退避因子0.5
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    session.headers = {'User-Agent': UserAgent().random}  # 使用随机用户代理
    return session

def download_music(song, directory, session):
    """
    根据歌曲信息和会话，下载音乐文件到指定目录。
    参数：
    - song: 歌曲信息的字典，包含标题和URL。
    - directory: 保存音乐文件的目录。
    - session: 用于HTTP请求的会话。
    """
    song_title = song['title']
    url = song['url']
    # 清理文件名中的不合法字符
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
            else:
                print(f"URL缺少必要参数：{safe_song_title}")

    except requests.exceptions.RequestException as e:
        print(f"下载错误 {safe_song_title}: {e}")

def main(target_directory, save_directory):
    """
    主函数，遍历指定目录中的JSON文件，解析歌曲数据，并调用下载功能。
    参数：
    - target_directory: 包含JSON文件的目录。
    - save_directory: 保存下载的音乐的目录。
    """
    session = get_session()
    for filename in os.listdir(target_directory):
        if filename.endswith('.json'):
            album_title = filename[:-5]  # 去掉文件后缀获取专辑标题
            json_path = os.path.join(target_directory, filename)
            with open(json_path, 'r', encoding='utf-8') as f:
                songs = json.load(f)
                directory = os.path.join(save_directory, album_title)
                if not os.path.exists(directory):
                    os.makedirs(directory)

                for song in songs:
                    # time.sleep(1)  # 可以取消注释来添加请求间隔，防止过快请求
                    download_music(song, directory, session)
    
    print("所有文件都已下载完毕")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="下载音乐文件到指定目录。")
    parser.add_argument('-t', '--targetDir', type=str, default="target", help="包含音乐数据 JSON 文件的目录")
    parser.add_argument('-s', '--saveDir', type=str, default="music", help="保存音乐文件的目录")
    args = parser.parse_args()

    main(args.targetDir, args.saveDir)
