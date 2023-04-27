import json
import discord.context_managers
from config import *
from datetime import datetime
import time
import yaml
from typing import Union
import asyncio
import threading
from discord.channel import DMChannel, TextChannel


def get_channel_context_path(channel_id: int) -> str:
    return f'./{DIRECTORY_CONTEXT}/{channel_id}.json'


def get_channel_setting_path(channel_id: int) -> str:
    return f'./{DIRECTORY_SETTING}/{channel_id}.json'


def makedirs(directory: str):
    if not os.path.exists(directory):
        os.makedirs(directory)


def jsonl_append_json(dirname: str, channel_id: int, new_item: list):
    makedirs(dirname)
    with open(os.path.join(dirname, f'{channel_id}.jsonl'),
              'a+',
              encoding='utf-8') as f:
        json.dump(new_item, f, ensure_ascii=False)
        # 加上换行符
        f.write('\n')


def extract_openai_chat_response_content(response):
    response_content = '\n\n'.join(
            [choice.message.content or 'None' for choice in response.choices])
    return response_content


def time_id() -> str:
    current_timestamp = time.time()
    formatted_time = datetime.fromtimestamp(current_timestamp).strftime(
            '%Y%m%d%H%M%S')
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


async def save_channel_info(channel):
    try:
        channel_id = channel.id

        info = {
            'name'   : extract_channel_name(channel),
            'id'     : channel.id,
            'topic'  : extract_channel_topic(channel),
            'type'   : str(type(channel)),
            'members': await get_channel_member_list(channel)
        }
        if channel.guild is not None:
            info['guild'] = {
                'id'         : channel.guild.id,
                'name'       : channel.guild.name,
                'description': channel.guild.description,
                'members'    : await get_guild_member_list(channel.guild),
            },

        makedirs(DIRECTORY_INFO)

        with open(os.path.join(DIRECTORY_INFO, f'{channel_id}.json'), 'w', encoding='utf-8') as f:
            json.dump(info, f, ensure_ascii=False)
    except:
        return


def get_channel_context(channel_id: int) -> list:
    filepath = get_channel_context_path(channel_id=channel_id)
    history = []
    if os.path.isfile(filepath):
        with open(filepath, 'r') as file:
            history = json.load(file)
            if not isinstance(history, list):
                # 历史数据不是列表
                history = []
                save_channel_context(channel_id=channel_id, history=history)
    return history


def convert_channel_history_to_content(history: list) -> str:
    return '\n'.join([f"{msg['role']}: {msg['content']}" for msg in history])


def save_channel_context(channel_id: int, history: list):
    makedirs(DIRECTORY_CONTEXT)
    with open(get_channel_context_path(channel_id=channel_id),
              'w',
              encoding='utf-8') as file:
        json.dump(history, file, ensure_ascii=False, indent=4)


# 获取频道成员列表
async def get_channel_member_list(channel):
    try:
        member_list = []
        async for member in channel.fetch_members():
            member_list.append(member)

        member_nicknames = [member.nick or member.name for member in member_list]

        return member_nicknames
    except:
        return []


async def get_guild_member_list(guild):
    try:
        member_list = []
        async for member in guild.fetch_members():
            member_list.append(member)

        member_nicknames = [member.nick or member.name for member in member_list]

        return member_nicknames
    except:
        return []


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


async def discord_send_message(
        source: Union[int, discord.Interaction, discord.TextChannel, discord.DMChannel],
        content: str) -> discord.Message:
    chunks = discord_split_contents(content)
    message = None
    if isinstance(source, discord.Interaction):
        for chunk in chunks:
            # ephemeral=True表示只有用户自己能看到这个消息
            message = await source.response.send_message(chunk, ephemeral=False)
    else:
        # channel
        for chunk in chunks:
            message = await source.send(chunk)

    return message


async def get_openai_image(prompt: str, width: int, height: int):
    try:
        if width > 1024:
            width = 1024
        if height > 1024:
            height = 1024

        def call():
            print(f'get_openai_image thread={threading.current_thread().name}')
            switch_openai_key()
            return openai.Image.create(prompt=f'{prompt}',
                                       n=1,
                                       size=f"{width}x{height}")

        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, call)
        # response = openai.Image.create(prompt=f'{prompt}',
        #                                n=1,
        #                                size=f"{width}x{height}")
        return response
    except ConnectionError as ce:
        return "无法连接到ChatGPT API。"
    except TimeoutError as te:
        return "ChatGPT API请求超时。"
    except Exception as e:
        return f"ChatGPT API请求失败: {e}"


# openai聊天模型
async def get_openai_chat_completion(
        channel_id: int,
        history: list,
        system: str = '',
        gpt_model: str = DEFAULT_GPT_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
        save_data: bool = True):
    def call(messages: list):
        print(f'get_openai_chat_completion thread={threading.current_thread().name}')
        switch_openai_key()
        return openai.ChatCompletion.create(
                model=gpt_model,
                messages=messages,
                temperature=temperature)

    try:
        # clone
        post_messages = list(history)
        if system != '':
            post_messages = [{
                'role'   : 'system',
                'content': system
            }] + post_messages

        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, call, post_messages)

        for choice in response.choices:
            post_messages.append(choice.message)
        if save_data:
            # 将数据永久保存下来，方便以后用来训练
            jsonl_append_json(dirname=DIRECTORY_HISTORY,
                              channel_id=channel_id,
                              new_item=post_messages)

        return response
    except ConnectionError as ce:
        return "无法连接到ChatGPT API。"
    except TimeoutError as te:
        return "ChatGPT API请求超时。"
    except Exception as e:
        print(e, system, history)
        return f"ChatGPT API请求失败: {e}"


def extract_channel_gpt_model(channel_name: str) -> str:
    gpt_model = DEFAULT_GPT_MODEL
    for model_id in available_model_ids:
        if model_id.replace(".", "-") in channel_name:
            gpt_model = model_id
            break
    return gpt_model


def extract_channel_name(channel) -> str:
    if isinstance(channel, DMChannel):
        return str(channel.id)
    else:
        try:
            return channel.name
        except:
            return str(channel.id)


def extract_channel_topic(channel) -> str:
    if isinstance(channel, DMChannel):
        return ''
    else:
        try:
            return channel.topic or ''
        except:
            return ''


def clear_history_by_reserve(history: list, reserve: int) -> list:
    # 保留系统
    system_history = []
    other_history = []
    for h in history:
        if h['role'] == 'system':
            system_history.append(h)
        else:
            other_history.append(h)

    if reserve > 0:
        other_history = other_history[-reserve:]
    elif reserve < 0:
        other_history = other_history[:reserve]
    else:
        other_history = []

    return system_history + other_history
