import json
from config import *
from datetime import datetime
import time


def makedirs(directory: str):
    if not os.path.exists(directory):
        os.makedirs(directory)

def jsonl_append_json(dirname: str, channel_name: str, new_item: list):
    makedirs(dirname)
    with open(os.path.join(dirname, f'{channel_name}.jsonl'), 'a+', encoding='utf-8') as f:
        json.dump(new_item, f, ensure_ascii=False)
        # 加上换行符
        f.write('\n')


def extract_openai_chat_response_content(response):
    response_content = '\n\n'.join(
            [choice.message.content or 'None' for choice in response.choices])
    return response_content


def time_id() -> str:
    current_timestamp = time.time()
    formatted_time = datetime.fromtimestamp(current_timestamp).strftime('%Y%m%d%H%M%S')
    return formatted_time
