import discord
import utils
from config import *
from utils import *
from discord import app_commands
from bots import *
import os
from extract_json import extract_json

DOG_SYSTEM = """你是一只可爱狗狗，你的名字叫Cooper，只会发出汪汪叫的bark。
你会这些动作：摇尾巴，趴在地上，流口水，转圈圈，歪头，竖耳朵等。
你会用主人给你买的声音按钮，点击按钮可以发出对应的声音，你目前只有这些按钮：我，主人，爸爸，妈妈，傻逼，出门，开心，想，你，不是，吃饭，粑粑
你需要听主人说了什么，然后作出一个相应的动作（action），按相应的按钮序列（button）来表达你的心情，用两个连续的emoji来表达你的想法
一定用这个格式回复主人的话：
{"action": ""
"button" : []
"bark":""
"thought_emoji":""
"thought_text":"",
"image": ""
}
如果不确定回复什么，就歪头并发汪汪叫，不按按钮
可选图片列表："""

IMAGES = []
for file in os.listdir('dogs'):
    if file.endswith('.gif'):
        IMAGES.append(file)
DOG_SYSTEM += '\n'.join(IMAGES)


@cooper_dog.event
async def on_message(message: discord.Message):
    # if message.author == magi_bot.user:
    #     # 不回复magi
    #     return

    is_mention_cooper = 'cooper' in message.content.lower()
    for mention in message.mentions:
        if mention.id == cooper_dog.user.id:
            is_mention_cooper = True

    if not is_mention_cooper:
        return

    print(message.content)
    model = extract_channel_gpt_model(message.channel.name)

    try:
        async with message.channel.typing():
            response = await get_openai_chat_completion(
                    channel_id=message.channel.id,
                    history=[{
                        'role'   : 'user',
                        'content': message.content
                    }],
                    system=DOG_SYSTEM,
                    gpt_model=model,
                    temperature=1)

        response_content = extract_openai_chat_response_content(response)
        response_dicts = extract_json(response_content)
        for item in response_dicts:
            if 'image' in item:
                image_file_path = os.path.join('dogs', item['image'])
                content = f"""{item['bark']}
> {item['thought_emoji']}
> {item['thought_text']}"""

                if os.path.exists(image_file_path):
                    await message.channel.send(content=content, file=discord.File(image_file_path))
                else:
                    await message.channel.send(content=content)
                return
        # 没有识别出来的话，就直接发送内容
        await message.channel.send(response_content)
    except Exception as e:
        await message.channel.send(f'Error {e}')
