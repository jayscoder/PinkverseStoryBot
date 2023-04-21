import json

import discord.context_managers

from config import *
from datetime import datetime
import time
import yaml
from typing import Union
import asyncio


def get_channel_context_path(channel_id: int) -> str:
    return f'./{DIRECTORY_CONTEXT}/{channel_id}.json'


def get_channel_setting_path(channel_id: int) -> str:
    return f'./{DIRECTORY_SETTING}/{channel_id}.json'


def makedirs(directory: str):
    if not os.path.exists(directory):
        os.makedirs(directory)


def jsonl_append_json(dirname: str, channel_name: str, new_item: list):
    makedirs(dirname)
    with open(os.path.join(dirname, f'{channel_name}.jsonl'),
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
async def get_channel_member_list(channel_id: int):
    member_list = []

    async for member in bot.get_channel(channel_id).fetch_members():
        member_list.append(member)

    member_nicknames = [member.nick or member.name for member in member_list]

    return member_nicknames


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


async def discord_send_message(source: Union[int, discord.Interaction, discord.TextChannel],
                               content: str) -> discord.Message:
    chunks = discord_split_contents(content)
    message = None
    if isinstance(source, int):
        # channel_id
        for chunk in chunks:
            message = await bot.get_channel(source).send(chunk)
    elif isinstance(source, discord.Interaction):
        for chunk in chunks:
            # ephemeral=True表示只有用户自己能看到这个消息
            message = await source.response.send_message(chunk, ephemeral=False)
    else:
        # channel
        for chunk in chunks:
            message = await source.send(chunk)

    return message


def get_openai_image(prompt: str, width: int, height: int):
    switch_openai_key()
    try:
        if width > 1024:
            width = 1024
        if height > 1024:
            height = 1024
        response = openai.Image.create(prompt=f'{prompt}',
                                       n=1,
                                       size=f"{width}x{height}")
        return response
    except ConnectionError as ce:
        return "无法连接到ChatGPT API。"
    except TimeoutError as te:
        return "ChatGPT API请求超时。"
    except Exception as e:
        return f"ChatGPT API请求失败: {e}"


# openai聊天模型
def get_openai_chat_completion(channel_name: str, history: list, system: str,
                               gpt_model: str, temperature: float):
    switch_openai_key()
    try:
        # clone
        post_messages = list(history)
        if system != '':
            post_messages = [{
                'role'   : 'system',
                'content': system
            }] + post_messages
        print(f'gpt_model={gpt_model}', post_messages)
        response = openai.ChatCompletion.create(model=gpt_model,
                                                messages=post_messages,
                                                temperature=temperature)

        for choice in response.choices:
            post_messages.append(choice.message)

        # 将数据永久保存下来，方便以后用来训练
        jsonl_append_json(dirname=DIRECTORY_HISTORY,
                          channel_name=channel_name,
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


# def channel_typing(channel_id: int) -> discord.context_managers.Typing:
#     channel = bot.get_channel(channel_id)
#     return channel.typing()

def _loading_done_callback(fut: asyncio.Future) -> None:
    # just retrieve any exception and call it a day
    try:
        fut.exception()
    except (asyncio.CancelledError, Exception):
        pass


class BotThinking:
    def __init__(self, channel_id: int, content: str):
        self.start_time = 0
        self.dots = 0
        self.channel_id = channel_id
        self.content = get_brief(content)
        self.message = None

    async def do_thinking(self) -> None:
        while True:
            await self.send_thinking()
            await asyncio.sleep(1)

    async def send_thinking(self):
        now = time.time()
        self.dots = (self.dots + 1) % 6
        dots_str = '.' * (self.dots + 1)
        content = f'\n> bot思考中️{dots_str}: {self.content} ({round((now - self.start_time))}s)'
        if self.message is None:
            self.message = await discord_send_message(source=self.channel_id, content=content)
        else:
            await self.message.edit(content=content)

    async def __aenter__(self) -> None:
        print('BotThinkingEnter', self.content)
        self.start_time = time.time()
        self.task: asyncio.Task[None] = asyncio.create_task(self.do_thinking())
        self.task.add_done_callback(_loading_done_callback)

    async def __aexit__(
            self,
            exc_type,
            exc,
            traceback,
    ) -> None:
        print('BotThinkingExit', self.content)
        self.task.cancel()
        if self.message is not None:
            await self.message.delete()


def get_brief(content: str):
    if len(content) > 15:
        return content[:15] + '...'
    else:
        return content
