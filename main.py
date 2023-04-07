import constantly
import discord
import os
import openai
import time
import json
import asyncio
import re
from discord.ext import commands
from enum import Flag, auto

openai.api_key = os.getenv("OPENAI_API_KEY")
bot = discord.Client(
    intents=discord.Intents.all()
)  # 指定了客户端对象需要接收所有的事件，包括一些敏感信息，例如用户列表、权限等等。需要注意的是，Discord在2022年4月7日之后，所有新创建的应用必须填写和审核 Intents 后才能使用它们。

available_models = openai.Model.list()['data']  # 当前支持的模型类型
available_model_ids = [model.id for model in available_models]


# 全局配置
class Config(constantly.NamedConstant):
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
    '''
    DEFAULT_GPT_MODEL = 'gpt-3.5-turbo'  # 默认是gpt-3.5

    # 默认GPT系统
    DEFAULT_GROUP_GPT_SYSTEM = "user文本第一行冒号前的内容是发送者名称"
    DEFAULT_GPT_SYSTEM = "You're a helpful assistant."

    CHANNEL_NAME_GROUP = 'group'


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

    @staticmethod
    def check_equal(content: str, command: str):
        for c in [command, f'!{command}', f'！{command}']:
            if content == c:
                return True
        return False

    @staticmethod
    def check_startswith(content: str, command: str):
        for c in [command, f'!{command}', f'！{command}']:
            if content.startswith(c):
                return True
        return False


# 频道类型(标志类型)
class ChannelMode(Flag):
    DEFAULT = auto()  # 默认频道类型
    GROUP = auto()  # GROUP频道类型
    NO_HISTORY = auto()  # 无上下文历史频道类型


# 上下文
class Context:
    DIRECTORY = 'data/context'  # 上下文文件夹

    def __init__(self, message: discord.Message):
        self.message = message
        self.content = message.content
        self.channel_name = message.channel.name
        self.file_path = f'./{Context.DIRECTORY}/{self.channel_name}.json'
        # 来自用户发的内容
        self.from_user = message.author != bot.user
        self.from_bot = message.author == bot.user

        self.channel_mode = ChannelMode.DEFAULT
        # 判断当前频道类型
        if 'group' in self.channel_name:
            self.channel_mode |= ChannelMode.GROUP

        if 'no-history' in self.channel_name:
            self.channel_mode |= ChannelMode.NO_HISTORY

        # 判断当前应该采用哪个gpt_model
        self.gpt_model = Config.DEFAULT_GPT_MODEL
        for model_id in available_model_ids:
            if model_id.replace(".", "-") in message.channel.name:
                self.gpt_model = model_id
                break

        # 加载历史数据
        self.history = []
        self.load_history()

        self.system = message.channel.topic or ''
        if self.system == '':
            if self.channel_mode & ChannelMode.GROUP:
                self.system = Config.DEFAULT_GROUP_GPT_SYSTEM
            else:
                self.system = Config.DEFAULT_GPT_SYSTEM

    def load_history(self):
        if self.channel_mode & ChannelMode.NO_HISTORY:
            # 无历史
            return

        if os.path.isfile(self.file_path):
            with open(self.file_path, 'r') as file:
                self.history = json.load(file)
                if not isinstance(self.history, list):
                    # 历史数据不是列表
                    self.history = []
                    self.dump_history()
        else:
            print(f'load_context:{self.channel_name} 文件不存在')
            self.history = []  # 返回一个空列表
            self.dump_history()

    def dump_history(self):
        if not os.path.exists(Context.DIRECTORY):
            os.makedirs(Context.DIRECTORY)
        with open(self.file_path, 'w', encoding='utf-8') as file:
            json.dump(self.history, file, ensure_ascii=False, indent=4)

    def history_content(self):
        return '\n'.join(
            [f"{msg['role']}: {msg['content']}" for msg in self.history])

    async def send_message(self, content: str):
        if len(content) <= Config.MAX_DISCORD_TOKENS:
            # 如果消息长度小于等于 2000，直接发送
            if content == '':
                content = '【空】'
            await self.message.channel.send(content)
        else:
            # 如果消息长度大于 2000，分割成多个小消息发送
            chunks = [
                content[i:i + Config.MAX_DISCORD_TOKENS]
                for i in range(0, len(content), Config.MAX_DISCORD_TOKENS)
            ]
            for chunk in chunks:
                await self.message.channel.send(chunk)

    # 获取成员列表
    async def get_member_list(self):
        member_list = []
        async for member in self.message.guild.fetch_members(limit=None):
            member_list.append(member)
        member_nicknames = [
            member.nick or member.name for member in member_list
        ]
        return member_nicknames

    # 截断历史，返回值：是否截断了
    def cut_off_history(self, max_tokens) -> bool:
        # 只保留最近N条消息，这N条消息的字符总数不能超过MAX_TOKENS
        max_tokens -= len(self.system)  # 要预留出system的空间
        temp_history = []
        temp_history_tokens = 0
        is_cut_off = False

        # 从最后一条消息开始遍历，只保留2000个字符
        for i in range(len(self.history) - 1, -1, -1):
            item_history = self.history[i]
            item_history['content'] = item_history['content'][:max_tokens]
            temp_history_tokens += len(item_history['content'])
            if temp_history_tokens > max_tokens:
                is_cut_off = True
                break
            temp_history.insert(0, item_history)
        self.history = temp_history
        self.dump_history()
        return is_cut_off

    # 获取当前历史token
    def history_tokens(self):
        return len(json.dumps(self.history)) + len(self.system)

    async def get_chat_completion(self):
        try:
            post_messages = [{
                'role': 'system',
                'content': self.system
            }] + self.history
            print(post_messages)
            response = openai.ChatCompletion.create(model=self.gpt_model,
                                                    messages=post_messages)
            return response
        except ConnectionError as ce:
            return "无法连接到ChatGPT API。"
        except TimeoutError as te:
            return "ChatGPT API请求超时。"
        except Exception as e:
            print(e, self.system, self.history)
            return f"ChatGPT API请求失败: {e}"


# def extract_model_id(string):
#     pattern = r'^modelretrieve:(\S+)$'
#     match = re.search(pattern, string)
#
#     if match:
#         model_id = match.group(1)
#         return model_id
#     else:
#         return None


# 定义bot登陆事件
@bot.event
async def on_ready():
    print('Logged in as {0.user}'.format(bot))
    for guild in bot.guilds:
        for channel in guild.text_channels:
            # if channel.name == '欢迎光临！':
            # await channel.send('我上线啦')
            print(channel)


# 定义bot接受到消息的事件
@bot.event
async def on_message(message: discord.Message):
    print(f'{message.channel.name}: {message.content}')
    context = Context(message)

    if context.channel_mode == ChannelMode.GROUP:
        # 群模式下需要添加群成员列表
        context.system += '\n群成员列表:\n' + '\n'.join(await
                                                   context.get_member_list())

    # 帮助命令
    if Command.check_equal(context.content, command=Command.HELP):
        await context.send_message(Config.HELP_CONTENT)
        return

    if Command.check_equal(context.content, Command.HISTORY):
        await context.send_message(context.history_content())
        return

    if Command.check_equal(context.content, Command.CURRENT_MODEL):
        await message.channel.send(f'当前使用的模型是: {context.gpt_model}')
        return

    if Command.check_equal(context.content, Command.LIST_MODELS):
        await context.send_message("\n".join(available_model_ids))
        return

    if Command.check_equal(context.content, Command.CLEAR):
        context.history = []
        context.dump_history()
        await context.send_message('已清空上下文')
        return

    if Command.check_equal(context.content, Command.MEMBERS):
        # 显式获取所有的成员信息
        member_list = await context.get_member_list()
        await context.send_message('\n'.join(member_list))
        return

    # modelId = extract_model_id(context.content)
    # if modelId:
    #     modelInfo = openai.Model.retrieve(modelId)
    #     print(modelInfo)
    #     await message.channel.send(json.dumps(modelInfo, indent=4))
    #     return

    summary = Command.check_equal(context.content, Command.SUMMARY)
    if summary:
        context.content = '请帮我将目前给你的上下文梳理成简短的几句话'

    # 如果是system命令
    if Command.check_equal(context.content, Command.SYSTEM):
        await context.send_message(context.system)
        return

    if Command.check_startswith(context.content, Command.TOKEN):
        tokens = context.history_tokens() + len(context.content) - 6
        await context.send_message(
            f'当前上下文token数: {tokens}\nGPT-4约花费{45 * 6.88 / 1000000 * tokens}人民币\nGPT-3.5约花费{2 * 6.88 / 1000000 * tokens}人民币\n当前使用的模型: {context.gpt_model}'
        )
        return

    if context.from_user:
        # 用户发的普通内容

        # 如果消息包含附件
        if message.attachments:
            for attachment in message.attachments:
                # 下载附件，处理附件的字节数据
                file_data = await attachment.read()
                # 如果需要读取文件的内容，请确保文件是可阅读的文本类型
                context.content += '\n' + file_data.decode("utf-8")

        if context.channel_mode == ChannelMode.GROUP:
            context.content = f'{message.author.name}: {context.content}'
        context.history.append({"role": 'user', "content": context.content})

    is_cut_off = context.cut_off_history(max_tokens=Config.MAX_GPT_TOKENS)
    if is_cut_off:
        await context.send_message(
            f"您上下文内容超过{Config.MAX_GPT_TOKENS}个字符，将对其进行截断")

    if context.from_bot:
        # 如果是机器人发的内容，则直接返回
        return

    # print(f'onMessage:{message.channel.name}', context.history)

    # async def send_typing():
    #     await asyncio.sleep(5)
    #     while True:
    #         print('思考中...')
    #         await message.channel.send('思考中...')
    #         await asyncio.sleep(5)

    async with message.channel.typing():
        # typing_task = asyncio.create_task(send_typing())
        response_task = asyncio.create_task(context.get_chat_completion())
        # 等待结果
        response = await response_task
        # typing_task.cancel()

    if isinstance(response, str):
        await context.send_message(response)
    elif len(response.choices) > 0:
        if summary:
            # 归纳整理
            context.history = []

        response_content = '\n\n'.join(
            [choice.message.content or 'None' for choice in response.choices])
        if not context.channel_mode & ChannelMode.NO_HISTORY:
            for choice in response.choices:
                context.history.append(choice.message)

        response_content += '\n' + f'> tokens={context.history_tokens()}'

        context.dump_history()
        await context.send_message(response_content)
    else:
        await context.send_message("ChatGPT API没有返回有效的响应。")


bot.run(os.getenv("DISCORD_STORY_BOT_TOKEN"))
