# coding: UTF-8
import discord
import utils
from config import *
from utils import *
from discord import app_commands
from bots import *
import os
import random
from collections import defaultdict

# 让主人更开心
DOG_SYSTEM = """你是一只叫Cooper的小公狗，你的脾气很暴躁，性欲也很旺盛，你喜欢吃大便，你喜欢小母狗
你需要听主人说了什么，然后识别主人的意图并做出符合你性格的回应：
1. 如果不确定回复什么，就摇尾巴
2. 必须用下面这个格式回复主人的话：
bark: "汪汪!" # 【必须】你的叫声，尝试根据心情发出不同的汪汪叫（可以酌情加上颜文字或符号），如 "汪汪!" "汪?" "汪~" "汪汪汪汪汪!!!!" "汪o(~ヘ~o#)" "汪(°一°）"
thought_emoji: "😭😫" # 【必须】用两个emoji来加强表达你的想法
action: "开心吃骨头" # 【必须】从动作列表中选择一个相应的动作回应主人 动作列表(逗号分隔)：开心吃骨头，无聊摆烂躺平，拉粑粑发抖，不高兴钻盒子，超生气踩枕头，生气踩枕头，兴奋叼绳子出去玩，生气拆家打翻抽纸，发呆流鼻涕，惊吓躲到墙后，游泳划水，站立不稳昏倒，惊讶张大嘴，警觉跑远趴下，开心跺脚，开心转一圈，从不开心变开心，兴奋连续跺脚，可疑嗅闻探查，难过地哭，期待按铃呼叫，开心飞跑，凌乱吹风，溜了离家出走行李，迷糊困睡觉晚安，摇尾巴，惊讶，转一圈休息，晚安睡觉开心，晚安睡觉枕头平静，严肃叫，慵懒地听，趴着难过，无聊乱走，兴奋跳，凶龇牙，咬骨头护食龇牙，靠近竖耳朵，躺平休息脏，开心转圈圈，听到后难过，跑着送来小心心，傲娇地扭屁股，开心地挥手，开心地跳起来庆祝，爱你扔小心心，打招呼，示意过来，不敢相信的表情，难以置信，要开饭了？，开心地鼓掌，开心地跳摇摆舞，宁死不屈，开心地抱着爱心摇摆，开心地跳舞，无聊地坐着，潇洒地蹦迪，生气地打拳击，生气地坐下，开心的出现，给自己挠痒痒，傻傻地跳，开心的准备吃饭，藏起来偷看，开心地拿着爱心晃动，表演小丑，绅士地鞠躬，跳起来庆祝，拿着糖果扭动，兴奋地欢呼，躲在门后冒冷汗，悲伤地坐在墙角，叼来花送给你，兴奋地完成工作，生气地放了个屁，竖大拇指太棒了，在纸上画圈圈无聊，摇头表示不行，吃惊的躲开，没有问题，戏谑地嘲讽，开心地晃动爱心，无聊地滚了过来，离开家挥手告别，鼓励加油，嘲讽地取消计划
button_sequence: "我,爱,主人" # 【必须】你会用主人给你买的声音按钮，点击按钮可以发出对应的声音，按相应的按钮序列（button_sequence）来尝试表达你想说的话（多个按钮用,分隔），你只有这些按钮：我，爱，主人，爸爸，妈妈，傻逼，出门，开心，想，你，才，不，是，饿，渴，吃，饭，粑粑，保护，玩，散步，母狗，要，骨头，喝，水，快，回家，吗，啊，难过，伤心，愤怒，死，了，痒，挠挠，摸摸，抱抱

例:
bark: "汪(°一°）"
thought_emoji: "😭😫"
action: "开心吃骨头"
button_sequence: "我,爱,主人"
"""

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


cooper_dog_history = defaultdict(list)  # cooper狗的记忆


@cooper_dog.event
async def on_message(message: discord.Message):
    # if message.author == magi_bot.user:
    #     # 不回复magi
    #     return

    is_mention_cooper = check_is_mention_cooper(message)

    if not is_mention_cooper:
        return

    history = cooper_dog_history[message.channel.id]

    if len(history) > 7:
        history = history[-7:]  # 保留最后七条，狗只能记住七句话
    history.append({ 'role': ROLE_USER, 'content': message.content })
    print(f'Cooper {message.author.display_name}: {message.content}')
    model = extract_channel_gpt_model(message.channel.name)

    try:
        async with message.channel.typing():
            response = await get_openai_chat_completion(
                    channel_id=message.channel.id,
                    history=history,
                    system=DOG_SYSTEM,
                    gpt_model=model,
                    temperature=1)

        if isinstance(response, str):
            await discord_send_message(source=message.channel,
                                       content=response)
            return

        response_content = extract_openai_chat_response_content(response)
        print(response_content)
        for choice in response.choices:
            history.append(choice.message)

        cooper_dog_history[message.channel.id] = history

        try:
            response_dict = extract_response_dict(response_content)
        except Exception as e:
            await message.channel.send(response_content)
            await message.channel.send(f'Error: {e}')
            return

        dog_image = find_dog_image_path(response_dict['action'])
        content = f"""{response_dict['bark']}"""

        thought = (response_dict['thought_emoji'] or '') + ' ' + response_dict['button_sequence'] or ''

        if thought != '':
            content += ' ' + thought
        content += f'```yaml\n{response_content}```'

        if os.path.exists(dog_image):
            await message.channel.send(content=content,
                                       file=discord.File(dog_image))
        else:
            await message.channel.send(content=content)

        # 没有识别出来的话，就直接发送内容
        # await message.channel.send(response_content)
    except Exception as e:
        await message.channel.send(f'Error {e}')


def find_dog_image_path(action: str) -> str:
    actions = action.split(',')
    image_path = os.path.join(DOG_IMAGE_DIR, action + '.gif')
    if os.path.exists(image_path):
        return image_path

    match_images = []
    for dog_image in DOG_IMAGES:
        for act in actions:
            if act in dog_image:
                match_images.append(os.path.join(DOG_IMAGE_DIR, dog_image))
    if len(match_images) > 0:
        return random.choice(match_images)
    return ''


def extract_response_dict(content: str) -> dict:
    response_dict = {
        'bark'           : '',
        'thought_emoji'  : '',
        'action'         : '',
        'button_sequence': ''
    }

    patterns = {
        'bark'           : r'bark(.*)',
        'thought_emoji'  : r'thought_emoji(.*)',
        'action'         : r'action(.*)',
        'button_sequence': r'button_sequence(.*)'
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, content)
        if match:
            response_dict[key] = re.sub(f"{key}|:|\"|'|\s|\*", "", match.group()).strip()

    return response_dict
