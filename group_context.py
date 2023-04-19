import json

import discord

import config
from utils import *
import time


# 群聊上下文
class GroupContext:

    def __init__(self, message: discord.Message):
        self.message = message
        self.content = message.content
        self.channel_name = message.channel.name
        self.file_path = f'./{DIRECTORY_CONTEXT}/{self.channel_name}.json'
        # 来自用户发的内容
        self.from_user = message.author != bot.user
        self.from_bot = message.author == bot.user
        self.document = ''  # 文档里的内容
        self.setting = get_channel_setting(channel_id=message.channel.id)

        self.channel_mode = ChannelMode.DEFAULT
        # 判断当前频道类型
        if 'group' in self.channel_name:
            self.channel_mode |= ChannelMode.GROUP

        if 'no-history' in self.channel_name:
            self.channel_mode |= ChannelMode.NO_HISTORY

        # 判断当前应该采用哪个gpt_model
        self.gpt_model = DEFAULT_GPT_MODEL
        for model_id in available_model_ids:
            if model_id.replace(".", "-") in message.channel.name:
                self.gpt_model = model_id
                break

        # 加载历史数据
        self.history = []
        self.load_history()

        self.system = message.channel.topic or ''
        if self.system == '':
            if self.channel_mode & ChannelMode.GROUP:
                self.system = DEFAULT_GROUP_GPT_SYSTEM
            else:
                self.system = DEFAULT_GPT_SYSTEM

        self.is_eval = False  # 是否执行返回的代码

    def load_history(self):
        if self.channel_mode & ChannelMode.NO_HISTORY:
            # 无历史
            return

        if os.path.isfile(self.file_path):
            with open(self.file_path, 'r') as file:
                self.history = json.load(file)
                if not isinstance(self.history, list):
                    # 历史数据不是列表
                    self.history = []
                    self.dump_history()
        else:
            print(f'load_context:{self.channel_name} 文件不存在')
            self.history = []  # 返回一个空列表
            self.dump_history()

    def dump_history(self):
        makedirs(DIRECTORY_CONTEXT)
        with open(self.file_path, 'w', encoding='utf-8') as file:
            json.dump(self.history, file, ensure_ascii=False, indent=4)

    def history_content(self):
        return '\n'.join(
                [f"{msg['role']}: {msg['content']}" for msg in self.history])

    async def send_message(self, content: str):
        if len(content) <= MAX_DISCORD_TOKENS:
            # 如果消息长度小于等于 2000，直接发送
            if content == '':
                content = '【空】'
            await self.message.channel.send(content)
        else:
            # 如果消息长度大于 2000，分割成多个小消息发送
            chunks = [
                content[i:i + MAX_DISCORD_TOKENS]
                for i in range(0, len(content), MAX_DISCORD_TOKENS)
            ]
            for chunk in chunks:
                await self.message.channel.send(chunk)

    # 获取成员列表
    async def get_member_list(self):
        member_list = []
        async for member in self.message.guild.fetch_members(limit=None):
            member_list.append(member)
        member_nicknames = [
            member.nick or member.name for member in member_list
        ]
        return member_nicknames

    # # 截断历史，返回值：是否截断了
    # def cut_off_history(self, max_tokens) -> bool:
    #     # 只保留最近N条消息，这N条消息的字符总数不能超过MAX_TOKENS
    #     max_tokens -= len(self.system)  # 要预留出system的空间
    #     temp_history = []
    #     temp_history_tokens = 0
    #     is_cut_off = False
    #
    #     # 从最后一条消息开始遍历，只保留2000个字符
    #     for i in range(len(self.history) - 1, -1, -1):
    #         item_history = self.history[i]
    #         item_history['content'] = item_history['content'][:max_tokens]
    #         temp_history_tokens += len(item_history['content'])
    #         if temp_history_tokens > max_tokens:
    #             is_cut_off = True
    #             break
    #         temp_history.insert(0, item_history)
    #     self.history = temp_history
    #     self.dump_history()
    #     return is_cut_off

    # 获取当前历史token
    def history_tokens(self):
        tokens = 0
        for item in self.history:
            tokens += len(item['content'])
        return tokens + len(self.system)

    # openai聊天模型
    async def get_openai_chat_completion(self, history: list):
        try:
            post_messages = history
            if self.system != '':
                post_messages = [{
                    'role'   : 'system',
                    'content': self.system
                }] + post_messages

            response = openai.ChatCompletion.create(
                    model=self.gpt_model,
                    messages=post_messages,
                    user=f'{self.message.author.id}',
                    temperature=self.setting['temperature']
            )

            for choice in response.choices:
                post_messages.append(choice.message)

            # 将数据永久保存下来，方便以后用来训练
            jsonl_append_json(
                    dirname=config.DIRECTORY_HISTORY,
                    channel_name=self.channel_name,
                    new_item=post_messages)

            return response
        except ConnectionError as ce:
            return "无法连接到ChatGPT API。"
        except TimeoutError as te:
            return "ChatGPT API请求超时。"
        except Exception as e:
            print(e, self.system, self.history)
            return f"ChatGPT API请求失败: {e}"

    async def get_openai_image(self, width: int, height: int):
        try:
            if width > 1024:
                width = 1024
            if height > 1024:
                height = 1024
            response = openai.Image.create(
                    prompt=f'{self.content}',
                    n=1,
                    size=f"{width}x{height}"
            )
            print(response)
            return response
        except ConnectionError as ce:
            return "无法连接到ChatGPT API。"
        except TimeoutError as te:
            return "ChatGPT API请求超时。"
        except Exception as e:
            print(e, self.system, self.history)
            return f"ChatGPT API请求失败: {e}"

    # on_message事件
    async def on_message(self):
        if self.channel_mode == ChannelMode.GROUP:
            # 群模式下需要添加群成员列表
            self.system += '\n群成员列表:\n' + '\n'.join(await
                                                         self.get_member_list())

        # 帮助命令
        if Command.check_equal(self.content, command=Command.HELP):
            await self.send_message(HELP_CONTENT)
            return

        if Command.check_equal(self.content, Command.HISTORY):
            await self.send_message(self.history_content())
            return

        if Command.check_equal(self.content, Command.CURRENT_MODEL):
            await self.send_message(f'当前使用的模型是: {self.gpt_model}')
            return

        if Command.check_equal(self.content, Command.LIST_MODELS):
            await self.send_message("\n".join(available_model_ids))
            return

        if Command.check_equal(self.content, Command.CLEAR):
            self.history = []
            self.dump_history()
            await self.send_message('已清空上下文')
            return

        if Command.check_equal(self.content, Command.MEMBERS):
            # 显式获取所有的成员信息
            member_list = await self.get_member_list()
            await self.send_message('\n'.join(member_list))
            return

        # 如果是system命令
        if Command.check_equal(self.content, Command.SYSTEM):
            await self.send_message(self.system)
            return

        is_summary = Command.check_equal(self.content, Command.SUMMARY)
        if is_summary:
            self.content = SUMMARY_CONTENT

        if Command.check_startswith(self.content, Command.TOKEN):
            self.content = Command.remove_startswith(self.content, Command.TOKEN)
            tokens = self.history_tokens() + len(self.content)
            await self.send_message(
                    f'当前上下文token数: {tokens}\nGPT-4约花费{GPT_4_TOKEN_PRICE * tokens}人民币\nGPT-3.5约花费{GPT_3_5_TOKEN_PRICE * tokens}人民币\n当前使用的模型: {self.gpt_model}'
            )
            return

        is_long = Command.check_startswith(self.content, Command.LONG)
        if is_long:
            self.content = Command.remove_startswith(self.content, Command.LONG)

        # 如果消息包含附件
        if self.message.attachments:
            for attachment in self.message.attachments:
                # 下载附件，处理附件的字节数据
                file_data = await attachment.read()
                # 如果需要读取文件的内容，请确保文件是可阅读的文本类型
                self.document += '\n' + file_data.decode("utf-8")

        if self.from_user:
            # 用户发的普通内容
            if self.channel_mode == ChannelMode.GROUP:
                self.content = f'{self.message.author.name}: {self.content}'

        if Command.check_startswith(self.content, Command.IMAGINE):
            width, height, self.content = Command.parse_imagine(self.content)
            async with self.message.channel.typing():
                response = await self.get_openai_image(width=width, height=height)
            # 生成图片
            if isinstance(response, str):
                await self.send_message(response)
            else:
                response_content = '\n'.join([item['url'] for i, item in enumerate(response['data'])])
                await self.send_message(response_content)
                return

        if self.from_bot:
            # 如果是机器人发的内容，则直接返回
            return

        if not is_long:
            # 不是处理大文本
            if self.document != '':
                self.history.append({ "role": 'user', "content": self.document + '\n' + self.content })
            else:
                self.history.append({ "role": 'user', "content": self.content })

            async with self.message.channel.typing():
                response = await self.get_openai_chat_completion(history=self.history)

            if isinstance(response, str):
                await self.send_message(response)
            elif len(response.choices) == 0:
                await self.send_message("ChatGPT API没有返回有效的响应。")
            else:

                response_content = extract_openai_chat_response_content(response)

                if not self.channel_mode & ChannelMode.NO_HISTORY:
                    for choice in response.choices:
                        self.history.append(choice.message)

                if is_summary:
                    # 归纳整理
                    self.history = [{ 'role': 'system', 'content': response_content }]

                completion_tokens = response['usage']['completion_tokens']
                prompt_tokens = response['usage']['prompt_tokens']
                total_tokens = response['usage']['total_tokens']
                current_model = response['model']

                response_content += f'''
    > tokens: {completion_tokens} + {prompt_tokens} = {total_tokens}
    > model: {current_model}
    > GPT-3.5: {total_tokens * GPT_3_5_TOKEN_PRICE}
    > GPT-4: ¥{total_tokens * GPT_4_TOKEN_PRICE}'''
                self.dump_history()
                await self.send_message(response_content)
        else:
            if self.document == '':
                await self.send_message('大文本内容需要放在文件里上传')
                return

            # 处理大文本（大文本内容在document里）（本次处理不会放到context历史里，但是会考虑上下文）
            completion_tokens = 0
            prompt_tokens = 0
            total_tokens = 0
            current_model = ''
            summary = ''

            lines = []

            for line in self.document.splitlines():
                line = line.strip()
                if line == '':
                    continue
                if len(lines) == 0:
                    lines.append(line)
                    continue
                if len(lines[-1] + '\n' + line) < 1000:
                    # 同时最多只处理1000个字符
                    lines[-1] += '\n' + line
                    continue
                lines.append(line)

            if len(lines) == 0:
                await self.send_message('大文本内容不能为空')
                return

            results = []

            for line in lines:
                post_history = self.history

                if summary != '':
                    post_history = [{
                        'role'   : 'system',
                        'content': summary
                    }]

                post_history += [{
                    'role'   : 'user',
                    'content': line + '\n' + self.content
                }]

                async with self.message.channel.typing():
                    response = await self.get_openai_chat_completion(
                            history=post_history)

                if isinstance(response, str):
                    await self.send_message(response)
                    break
                elif len(response.choices) == 0:
                    await self.send_message("ChatGPT API没有返回有效的响应。")
                    break

                response_content = extract_openai_chat_response_content(response)
                results.append(response_content)
                await self.send_message(response_content)
                completion_tokens += response['usage']['completion_tokens']
                prompt_tokens += response['usage']['prompt_tokens']
                total_tokens += response['usage']['total_tokens']
                current_model = response['model']

                for choice in response.choices:
                    post_history.append(choice.message)

                # 总结一下
                async with self.message.channel.typing():
                    response = await self.get_openai_chat_completion(
                            history=post_history + [{ 'role': 'user', 'content': SUMMARY_CONTENT }])

                if isinstance(response, str):
                    await self.send_message(response)
                    break
                elif len(response.choices) == 0:
                    await self.send_message("ChatGPT API没有返回有效的响应。")
                    break

                summary = extract_openai_chat_response_content(response)
                completion_tokens += response['usage']['completion_tokens']
                prompt_tokens += response['usage']['prompt_tokens']
                total_tokens += response['usage']['total_tokens']
                current_model = response['model']

            dirname = os.path.join(DIRECTORY_OUTPUT, self.channel_name)
            makedirs(dirname)
            filepath = os.path.join(dirname, time_id() + '.txt')
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('\n'.join(results))

            tokens_content = f'''
> tokens: {completion_tokens} + {prompt_tokens} = {total_tokens}
> model: {current_model}
> GPT-3.5: {total_tokens * GPT_3_5_TOKEN_PRICE}
> GPT-4: ¥{total_tokens * GPT_4_TOKEN_PRICE}
>
> {summary}'''
            await self.message.channel.send(tokens_content, file=discord.File(filepath))
