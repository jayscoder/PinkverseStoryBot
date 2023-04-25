import discord
import utils
from config import *
from utils import *
from magi_bot import magi_bot
from cooper_dog import cooper_dog


# if selected_option == 'temperature':
#     # 创建一个输入框让用户输入生成文本长度
#     input_length = discord.ui.TextInput(
#             placeholder="输入文本长度",
#             min_length=1,
#             max_length=3  # 生成文本长度最长为999
#     )
#     # 编辑之前的交互式消息来替换掉刚刚的 select
#     await message.edit(components=[input_length])
# elif selected_option == 'quantity':
#     # 创建一个输入框让用户输入生成文本数量
#     input_quantity = discord.ui.TextInput(
#             placeholder="输入文本数量",
#             min_length=1,
#             max_length=3  # 生成文本数量最多为999
#     )
#     # 编辑之前的交互式消息来替换掉刚刚的 select
#     await message.edit(components=[inpu
#                                    t_quantity])
# else:
#     # 如果选择了未知的选项，发送一条提醒
#     await inter.response.send_message('未知的选项', ephemeral=True)

async def launch_bots():
    await asyncio.gather(
            magi_bot.start(os.getenv("DISCORD_MAGI_BOT_TOKEN")),
            cooper_dog.start(os.getenv('DISCORD_COOPER_DOG_TOKEN'))
    )


if __name__ == '__main__':
    asyncio.run(launch_bots())
