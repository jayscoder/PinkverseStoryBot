import discord
import utils
from config import *
from utils import *
from discord import app_commands
from bots import *
import os
from extract_json import extract_json

DOG_SYSTEM = """你是一只可爱狗狗，你的名字叫Cooper，只会发出汪汪叫的bark。
你需要听主人说了什么，然后作出一个相应的回复
你要根据可选图片列表选择一个图片来回复主人（image）
一定用这个格式回复主人的话：
{
"bark":"",
"thought_emoji":"",
"thought_text":"",
"image": ""
}
如果不确定回复什么，就歪头并发汪汪叫
可选图片列表：
难过
不高兴
疑问
生气
不稳定
开心
兴奋
惊讶
快点
无聊
稳定
警觉
踩
躲
转圈圈
迷糊
喂喂
我在听"""

DOG_IMAGES = []
DOG_IMAGE_DIR = 'dogs'

for file in os.listdir(DOG_IMAGE_DIR):
    if file.endswith('.gif'):
        DOG_IMAGES.append(file)
# DOG_SYSTEM += '\n'.join(DOG_IMAGES)


# 定义bot登陆事件
@cooper_dog.event
async def on_ready():
    await cooper_dog_tree.sync()
    print('Cooper Logged in as {0.user}'.format(cooper_dog))


@cooper_dog.event
async def on_message(message: discord.Message):
    # if message.author == magi_bot.user:
    #     # 不回复magi
    #     return

    is_mention_cooper = check_is_mention_cooper(message)

    if not is_mention_cooper:
        return

    print(f'{message.author.display_name}: {message.content}')
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

        if isinstance(response, str):
            await discord_send_message(source=message.channel, content=response)
            return

        response_content = extract_openai_chat_response_content(response)
        response_dicts = extract_json(response_content)
        for item in response_dicts:
            if 'image' in item:
                dog_image = find_dog_image_path(item['image'])
                content = f"""{item['bark']}"""
                if item['thought_text'] or item['thought_emoji']:
                    content += f"""
> {item['thought_emoji'] + item['thought_text']}"""
                if os.path.exists(dog_image):
                    await message.channel.send(content=content, file=discord.File(dog_image))
                else:
                    await message.channel.send(content=content)
                return

        # 没有识别出来的话，就直接发送内容
        await message.channel.send(response_content)
    except Exception as e:
        await message.channel.send(f'Error {e}')


def find_dog_image_path(image: str) -> str:
    image_path = os.path.join(DOG_IMAGE_DIR, image)
    if os.path.exists(image_path):
        return image_path

    for dog_image in DOG_IMAGES:
        if image in dog_image:
            return os.path.join(DOG_IMAGE_DIR, dog_image)
    return ''
