import json

import discord

from config import *
from datetime import datetime
import time
import yaml
from typing import Union


def get_channel_history_path(channel_name: str) -> str:
    return f'./{DIRECTORY_CONTEXT}/{channel_name}.json'


def get_channel_setting_path(channel_id: int) -> str:
    return f'./{DIRECTORY_SETTING}/{channel_id}.json'


def makedirs(directory: str):
    if not os.path.exists(directory):
        os.makedirs(directory)


def jsonl_append_json(dirname: str, channel_name: str, new_item: list):
    makedirs(dirname)
    with open(os.path.join(dirname, f'{channel_name}.jsonl'), 'a+', encoding='utf-8') as f:
        json.dump(new_item, f, ensure_ascii=False)
        # 加上换行符
        f.write('\n')


def extract_openai_chat_response_content(response):
    response_content = '\n\n'.join(
            [choice.message.content or 'None' for choice in response.choices])
    return response_content


def time_id() -> str:
    current_timestamp = time.time()
    formatted_time = datetime.fromtimestamp(current_timestamp).strftime('%Y%m%d%H%M%S')
    return formatted_time


def get_channel_setting(channel_id: int) -> dict:
    filename = get_channel_setting_path(channel_id=channel_id)
    data = { }
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
    if 'temperature' not in data:
        data['temperature'] = 1
    return data


def save_channel_setting(channel_id: int, setting: dict):
    makedirs(DIRECTORY_SETTING)
    filename = get_channel_setting_path(channel_id=channel_id)
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(setting, f, ensure_ascii=False)


def get_channel_history(channel_name: str) -> list:
    filepath = get_channel_history_path(channel_name=channel_name)
    history = []
    if os.path.isfile(filepath):
        with open(filepath, 'r') as file:
            history = json.load(file)
            if not isinstance(history, list):
                # 历史数据不是列表
                history = []
                save_channel_history(channel_name=channel_name, history=history)
    return history


def get_channel_history_content(history: list) -> str:
    return '\n'.join(
            [f"{msg['role']}: {msg['content']}" for msg in history])


def save_channel_history(channel_name: str, history: list):
    makedirs(DIRECTORY_CONTEXT)
    with open(get_channel_history_path(channel_name=channel_name), 'w', encoding='utf-8') as file:
        json.dump(history, file, ensure_ascii=False, indent=4)


# 获取频道成员列表
async def get_channel_member_list(channel_id: int):
    member_list = []

    async for member in bot.get_channel(channel_id).fetch_members():
        member_list.append(member)

    member_nicknames = [
        member.nick or member.name for member in member_list
    ]

    return member_nicknames


def get_openai_image(prompt: str, width: int, height: int):
    try:
        if width > 1024:
            width = 1024
        if height > 1024:
            height = 1024
        response = openai.Image.create(
                prompt=f'{prompt}',
                n=1,
                size=f"{width}x{height}"
        )
        return response
    except ConnectionError as ce:
        return "无法连接到ChatGPT API。"
    except TimeoutError as te:
        return "ChatGPT API请求超时。"
    except Exception as e:
        return f"ChatGPT API请求失败: {e}"


def discord_split_contents(content: str) -> [str]:
    if len(content) <= MAX_DISCORD_TOKENS:
        # 如果消息长度小于等于 2000，直接发送
        if content == '':
            content = '【空】'

        return [content]
    else:
        # 如果消息长度大于 2000，分割成多个小消息发送
        chunks = [
            content[i:i + MAX_DISCORD_TOKENS]
            for i in range(0, len(content), MAX_DISCORD_TOKENS)
        ]
        return chunks


async def discord_send_message(source: Union[int, discord.Interaction], content: str):
    chunks = discord_split_contents(content)
    if isinstance(source, int):
        # channel_id
        for chunk in chunks:
            await bot.get_channel(source).send(chunk)
    elif isinstance(source, discord.Interaction):
        for chunk in chunks:
            await source.response.send_message(chunk)
