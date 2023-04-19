import json
from config import *

def makedirs(directory: str):
    if not os.path.exists(directory):
        os.makedirs(directory)

def jsonl_append_json(dirname: str, channel_name: str, new_item: list):
    makedirs(dirname)
    with open(os.path.join(dirname, f'{channel_name}.jsonl'), 'a+', encoding='utf-8') as f:
        json.dump(new_item, f)
        # 加上换行符
        f.write('\n')
