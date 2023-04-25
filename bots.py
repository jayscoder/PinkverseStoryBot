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
