import discord
import utils
from config import *
from utils import *
from discord import app_commands
from bots import *
import os
from extract_json import extract_json
import random

DOG_SYSTEM = """你是一只狗狗，你的名字叫Cooper，只会汪汪叫。
你需要听主人说了什么，然后从动作列表中作出一个相应的动作回应主人（action），按相应的按钮序列（button_sequence）来尝试表达你想说的话，用两个emoji来加强表达你的心情和想法（thought_emoji）
你会用主人给你买的声音按钮，点击按钮可以发出对应的声音，你目前只有这些按钮(button)：我，主人，爸爸，妈妈，傻逼，出门，开心，想，你，不是，吃饭，粑粑
如果不确定回复什么，就歪头并汪汪叫，不按按钮
一定用这个格式回复主人的话：
{
"bark":"",
"thought_emoji":"",
"action": "",
"button_sequence":[]
}
动作列表：开心吃骨头，无聊摆烂躺平，拉粑粑发抖，不高兴钻盒子，超生气踩枕头，生气踩枕头，兴奋叼绳子出去玩，生气拆家打翻抽纸，发呆流鼻涕，惊吓躲到墙后，游泳划水，站立不稳昏倒，惊讶张大嘴，警觉跑远趴下，开心跺脚，开心转一圈，从不开心变开心，兴奋连续跺脚，可疑嗅闻探查，难过地哭，期待按铃呼叫，开心飞跑，凌乱吹风，溜了离家出走行李，迷糊困睡觉晚安，摇尾巴，惊讶，转一圈休息，晚安睡觉开心，晚安睡觉枕头平静，严肃叫，慵懒地听，趴着难过，无聊乱走，兴奋跳，凶龇牙，咬骨头护食龇牙，靠近竖耳朵，躺平休息脏，开心转圈圈，听到后难过"""

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

    print(f'Cooper {message.author.display_name}: {message.content}')
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
            if 'action' in item:
                dog_image = find_dog_image_path(item['action'])
                content = f"""{item['bark']}"""

                thought = (item['thought_emoji'] or '') + ''.join(item['button_sequence'] or [])

                if thought != '':
                    content += f'\n> {thought}'

                # content += f" action={item['action']}"
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
    match_images = []
    for dog_image in DOG_IMAGES:
        if image in dog_image:
            match_images.append(os.path.join(DOG_IMAGE_DIR, dog_image))
    if len(match_images) > 0:
        return random.choice(match_images)
    return ''
