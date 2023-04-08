import openai
import os
import discord
import constantly
from enum import Flag, auto
import re

openai.api_key = os.getenv("OPENAI_API_KEY")
bot = discord.Client(
        intents=discord.Intents.all()
)  # 指定了客户端对象需要接收所有的事件，包括一些敏感信息，例如用户列表、权限等等。需要注意的是，Discord在2022年4月7日之后，所有新创建的应用必须填写和审核 Intents 后才能使用它们。

# 全局配置
MAX_GPT_TOKENS = 2000  # GPT最多上传2000个字符
MAX_DISCORD_TOKENS = 2000  # discord一次最多可以发送2000个字符的消息

HELP_CONTENT = '''!help: 获取当前的指令手册
!history: 获取上下文文件
!currentmodel: 获取当前使用的模型
!listmodels: 获取支持的模型列表
!summary: 帮我将目前的上下文梳理成简短的几句话，并重新设置上下文
!system: 获取当前的system（群简介）
!clear: 清空上下文
!token: 获取当前上下文token数
!members: 获取当前频道所有成员的名称
!imagine[400x500]: 生成400x500图片
!imagine[800]: 生成800x800图片
!imagine: 生成1024图片
'''

DEFAULT_GPT_MODEL = 'gpt-3.5-turbo'  # 默认是gpt-3.5

# 默认GPT系统
DEFAULT_GROUP_GPT_SYSTEM = "user文本第一行冒号前的内容是发送者名称"
# DEFAULT_GPT_SYSTEM = "You're a helpful assistant."
DEFAULT_GPT_SYSTEM = ''

CHANNEL_NAME_GROUP = 'group'

available_models = openai.Model.list()['data']  # 当前支持的模型类型
available_model_ids = [model.id for model in available_models]

GPT_4_TOKEN_PRICE = 45 * 6.88 / 1000000
GPT_3_5_TOKEN_PRICE = 2 * 6.88 / 1000000


DIRECTORY_DATA = 'data'
DIRECTORY_AUDIO = 'data/audio'
DIRECTORY_CONTEXT = 'data/context'


# 聊天命令
class Command(constantly.NamedConstant):
    HELP = 'help'
    HISTORY = 'history'
    CURRENT_MODEL = 'currentmodel'
    LIST_MODELS = 'listmodels'
    SUMMARY = 'summary'
    SYSTEM = 'system'
    CLEAR = 'clear'
    TOKEN = 'token'
    MEMBERS = 'members'
    IMAGINE = 'imagine' # 生成图片命令
    SPEAK = 'speak'

    @staticmethod
    def check_equal(content: str, command: str):
        for c in [f'!{command}', f'！{command}']:
            if content == c:
                return True
        return False

    @staticmethod
    def check_startswith(content: str, command: str):
        for c in [f'!{command}', f'！{command}']:
            if content.startswith(c):
                return True
        return False

    @staticmethod
    def remove_startswith(content: str, command: str):
        return content[len(command) + 1:].lstrip()

    @staticmethod
    def parse_imagine(text):
        pattern1 = r'^!imagine\[(\d+)x(\d+)\](.*)'
        pattern2 = r'^!imagine\[(\d+)\](.*)'
        pattern3 = r'^!imagine(.*)'
        match1 = re.match(pattern1, text)
        if match1:
            width, height, remaining = match1.groups()
            return int(width), int(height), remaining
        match2 = re.match(pattern2, text)
        if match2:
            size, remaining = match2.groups()
            return int(size), int(size), remaining
        match3 = re.match(pattern3, text)
        if match3:
            return 1024, 1024, match3.group(1)
        return None


# 频道类型(标志类型)
class ChannelMode(Flag):
    DEFAULT = auto()  # 默认频道类型
    GROUP = auto()  # GROUP频道类型
    NO_HISTORY = auto()  # 无上下文历史频道类型
