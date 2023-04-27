# coding: UTF-8
import re

DOG_SYSTEM = """你是一只叫Cooper的小狗，你很爱向主人撒娇，你需要听主人说了什么，然后识别主人的意图并做出让主人更开心的回应：
1. 如果不确定回复什么，就摇尾巴
2. 必须用下面这个格式回复主人的话：
bark: "汪汪!" # 【必须】你的叫声，尝试根据心情发出不同的汪汪叫，如 "汪汪!" "汪?" "汪~" "汪汪汪汪汪!!!!"
thought_emoji: "😭😫" # 【必须】用两个emoji来加强表达你的想法
action: "开心吃骨头" # 【必须】从动作列表中选择一个相应的动作回应主人 动作列表(逗号分隔)：开心吃骨头，无聊摆烂躺平，拉粑粑发抖，不高兴钻盒子，超生气踩枕头，生气踩枕头，兴奋叼绳子出去玩，生气拆家打翻抽纸，发呆流鼻涕，惊吓躲到墙后，游泳划水，站立不稳昏倒，惊讶张大嘴，警觉跑远趴下，开心跺脚，开心转一圈，从不开心变开心，兴奋连续跺脚，可疑嗅闻探查，难过地哭，期待按铃呼叫，开心飞跑，凌乱吹风，溜了离家出走行李，迷糊困睡觉晚安，摇尾巴，惊讶，转一圈休息，晚安睡觉开心，晚安睡觉枕头平静，严肃叫，慵懒地听，趴着难过，无聊乱走，兴奋跳，凶龇牙，咬骨头护食龇牙，靠近竖耳朵，躺平休息脏，开心转圈圈，听到后难过，跑着送来小心心，傲娇地扭屁股，开心地挥手，开心地跳起来庆祝，爱你扔小心心，打招呼，示意过来，不敢相信的表情，难以置信，要开饭了？，开心地鼓掌，开心地跳摇摆舞，宁死不屈，开心地抱着爱心摇摆，开心地跳舞，无聊地坐着，潇洒地蹦迪，生气地打拳击，生气地坐下，开心的出现，给自己挠痒痒，傻傻地跳，开心的准备吃饭，藏起来偷看，开心地拿着爱心晃动，表演小丑，绅士地鞠躬，跳起来庆祝，拿着糖果扭动，兴奋地欢呼，躲在门后冒冷汗，悲伤地坐在墙角，叼来花送给你，兴奋地完成工作，生气地放了个屁，竖大拇指太棒了，在纸上画圈圈无聊，摇头表示不行，吃惊的躲开，没有问题，戏谑地嘲讽，开心地晃动爱心，无聊地滚了过来，离开家挥手告别，鼓励加油，嘲讽地取消计划
button_sequence: "我,爱,主人" # 【必须】你会用主人给你买的声音按钮，点击按钮可以发出对应的声音，按相应的按钮序列（button_sequence）来尝试表达你想说的话（多个按钮用,分隔），你只有这些按钮：我，爱，主人，爸爸，妈妈，傻逼，出门，开心，想，你，才，不，是，饿，渴，吃，饭，粑粑，保护，玩，散步，母狗，要，骨头，喝，水，快，回家，吗，啊，难过，伤心，愤怒，死，了，痒，挠挠，摸摸，抱抱
"""


def extract_response_dict(content: str) -> dict:
    response_dict = {
        'bark'           : '',
        'thought_emoji'  : '',
        'action'         : '',
        'button_sequence': ''
    }
    bark_match = re.search(r'bark:(.*)', content)
    thought_emoji_match = re.search(r'thought_emoji:(.*)', content)
    action_match = re.search(r'action:(.*)', content)
    button_sequence_match = re.search(r'button_sequence:(.*)', content)

    if bark_match is not None:
        response_dict['bark'] = re.sub(r"bark:|\"|\'", "", bark_match.group()).strip()
    if thought_emoji_match is not None:
        response_dict['thought_emoji'] = re.sub(r"thought_emoji:|\"|\'", "", thought_emoji_match.group()).strip()
    if action_match is not None:
        response_dict['action'] = re.sub(r"action:|\"|\'", "", action_match.group()).strip()
    if button_sequence_match is not None:
        response_dict['button_sequence'] = re.sub(r"button_sequence:|\"|\'", "", button_sequence_match.group()).strip()

    return response_dict
    # yaml_text = re.match(r'(bark:.*\n)?(action:.*\n)?button_sequence:\s*\[.*\]',
    #                       content, re.DOTALL)
    # return yaml.safe_load(yaml_text)


if __name__ == '__main__':
    text = """bark: "汪~" 
thought_emoji: "😊🎉" 
action: "兴奋叼绳子出去玩" 
button_sequence: '玩,玩,玩'"""
    print(extract_response_dict(text))
