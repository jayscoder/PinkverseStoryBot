import discord
from config import *
from utils import *

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
    await context.on_message()


if __name__ == '__main__':
    bot.run(os.getenv("DISCORD_STORY_BOT_TOKEN"))
