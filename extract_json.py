'''提取出文本中的json'''
import json
from typing import Union, Optional
import re


def replace_single_quotes(match):
    match_str = match.group()
    if match_str.startswith("'") and match_str.endswith("'") and len(match_str) > 1:
        return '"' + match_str[1:-1] + '"'
    else:
        return match_str


# 使用正则表达式匹配JSON字符串

def extract_json(content: str) -> list:
    json_matches = re.findall(r'\{[\s\S]*?\}', content)
    results = []
    for json_str in json_matches:
        print(json_str)
        json_str = re.sub(r"'([^'\n]*)'", replace_single_quotes, json_str)  # 仅替换键和值中的单引号
        json_obj = json.loads(json_str)
        results.append(json_obj)
    return results


if __name__ == '__main__':
    sample_text = '''dadada{"name": 'hello'}下面是生成的内容
    {"action": "严肃",
    "button_sequence" : ["钱", '一起', '干活'],
    "voice":"努力工作，加班挣更多的钱！",
    "thought_emoji":"💰💰",
    "thought_text":"想要更多的钱"}
    （提示：请注意尊重自己和他人的合法权益及规则，不要做出违法违规的行为）'''

    print(extract_json(sample_text))
