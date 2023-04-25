from config import *
import discord
from discord import app_commands

# 指定了客户端对象需要接收所有的事件，包括一些敏感信息，例如用户列表、权限等等。需要注意的是，Discord在2022年4月7日之后，所有新创建的应用必须填写和审核 Intents 后才能使用它们。
magi_bot = discord.Client(
        intents=discord.Intents.all()
)
magi_bot_tree = app_commands.CommandTree(magi_bot)

# 指定了客户端对象需要接收所有的事件，包括一些敏感信息，例如用户列表、权限等等。需要注意的是，Discord在2022年4月7日之后，所有新创建的应用必须填写和审核 Intents 后才能使用它们。
cooper_dog = discord.Client(
        intents=discord.Intents.all()
)
cooper_dog_tree = app_commands.CommandTree(cooper_dog)


def check_is_mention_cooper(message: discord.Message):
    lower = message.content.lower()
    is_mention = lower.startswith('cooper') or lower.startswith('@cooper')
    # if len(message.mentions) > 0:
    #     if message.mentions[0].id == cooper_dog.user.id:
    #         is_mention = True
    for mention in message.mentions:
        if mention.id == cooper_dog.user.id:
            is_mention = True
    return is_mention


def check_is_mention_magi(message: discord.Message):
    lower = message.content.lower()
    is_mention = lower.startswith('magi') or lower.startswith('@magi')
    # if len(message.mentions) > 0:
    #     if message.mentions[0].id == magi_bot.user.id:
    #         is_mention = True
    for mention in message.mentions:
        if mention.id == magi_bot.user.id:
            is_mention = True
    return is_mention

# def is_mention_magi(message: discord.Message):
#     is_mention_magi = 'cooper' in message.content.lower()
#     for mention in message.mentions:
#         if mention.id == cooper_dog.user.id:
#             is_mention_cooper = True
#     return is_mention_cooper
