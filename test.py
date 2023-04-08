import re

import re

def parse_imagine(text):
    pattern1 = r'^!imagine\[(\d+)x(\d+)\](.*)'
    pattern2 = r'^!imagine\[(\d+)\](.*)'
    pattern3 = r'^!imagine(.*)'
    match1 = re.match(pattern1, text)
    if match1:
        width, height, remaining = match1.groups()
        return int(width), int(height), remaining
    match2 = re.match(pattern2, text)
    if match2:
        size, remaining = match2.groups()
        return int(size), int(size), remaining
    match3 = re.match(pattern3, text)
    if match3:
        return 1024, 1024, match3.group(1)
    return None

# 测试代码
text1 = "!imagine[500x600]some text"
text2 = "!imagine[333]some other text"
text3 = "!imagineyetanother text"
print(parse_imagine(text1)) # 输出 (500, 600, 'some text')
print(parse_imagine(text2)) # 输出 (800, 800, 'some other text')
print(parse_imagine(text3)) # 输出 (1024, 1024, 'yetanother text')

