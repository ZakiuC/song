import json
import re
import pyperclip
import argparse
import os
import sys

def extract_songs_and_title(input_text):
    """
    从给定的文本中按行处理和提取专辑标题和歌曲信息。
    文本格式预期为专辑标题在第一行，接着是空行，然后是歌曲信息。
    歌曲信息包括歌曲标题、调式描述和链接。

    参数:
    - input_text: 来自剪贴板或其他来源的文本数据。

    返回:
    - title: 提取的专辑标题。
    - songs: 歌曲信息列表，每个元素是一个包含歌曲标题和链接的字典。
    """
    lines = input_text.strip().split('\n')
    
    if not lines or not lines[0].startswith("《") or not lines[1].strip() == "":
        print("错误：第一行不是有效的专辑名")
        return "未知专辑", []
    
    title = lines[0].strip()
    print(f"提取到的专辑标题：{title}")
    
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
            print(f"添加歌曲信息：标题 - {full_title}, 链接 - {url_match.group(0)}")

    return title, songs

def save_as_json(songs, directory, filename):
    """
    将歌曲信息保存为JSON文件。

    参数:
    - songs: 包含歌曲标题和链接的列表。
    - directory: 保存JSON文件的目录。
    - filename: JSON文件的名称。

    返回:
    - file_path: 保存JSON文件的完整路径。
    """
    if not os.path.exists(directory):
        os.makedirs(directory)
    file_path = os.path.join(directory, filename)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(songs, f, ensure_ascii=False, indent=4)
    print(f"文件已保存到：{file_path}")
    return file_path

def main():
    """
    主函数，解析命令行参数，从剪贴板读取内容，提取歌曲信息，然后保存为JSON文件。
    """
    parser = argparse.ArgumentParser(description="保存歌曲信息到JSON文件")
    parser.add_argument('-t', '--targetDir', type=str, default="target", help="保存文件的目录")
    args = parser.parse_args()

    input_text = pyperclip.paste()
    print("读取剪贴板内容完成")

    album_title, songs = extract_songs_and_title(input_text)
    if not songs:
        print("错误：未能从剪贴板内容中提取有效的歌曲信息。")
        sys.exit(1)

    filename = f"{album_title}.json"
    saved_path = save_as_json(songs, args.targetDir, filename)
    print(f"已保存至：{saved_path}")

if __name__ == "__main__":
    main()
