from utils import *
from discord.channel import DMChannel, TextChannel

# 频道上下文
class ChannelContext:

    def __init__(self, message: discord.Message):
        self.message = message
        self.content = message.content
        self.channel_name = extract_channel_name(message.channel)

        self.channel_id = message.channel.id
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
        self.gpt_model = extract_channel_gpt_model(self.channel_name)

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
            self.history = []
            return
        self.history = get_channel_context(channel_id=self.channel_id)

    def dump_history(self):
        save_channel_context(channel_id=self.channel_id, history=self.history)

    def history_content(self):
        return convert_channel_history_to_content(history=self.history)

    async def send_message(self, content: str):
        await discord_send_message(source=self.channel_id, content=content)

    # 获取当前历史token
    def history_tokens(self):
        tokens = 0
        for item in self.history:
            tokens += len(item['content'])
        return tokens + len(self.system)

    # openai聊天模型
    async def get_openai_chat_completion(self, history: list):
        return await get_openai_chat_completion(
                channel_id=self.channel_id,
                history=history,
                system=self.system,
                gpt_model=self.gpt_model,
                temperature=self.setting['temperature'])

    # on_message事件
    async def on_message(self):
        if self.channel_mode == ChannelMode.GROUP:
            # 群模式下需要添加群成员列表
            self.system += '\n群成员列表:\n' + '\n'.join(await
                                                         get_channel_member_list(channel_id=self.channel_id))

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
            member_list = await get_channel_member_list(channel_id=self.channel_id)
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
                response = await get_openai_image(prompt=self.content, width=width, height=height)
            # 生成图片
            if isinstance(response, str):
                await self.send_message(response)
                return
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
                self.history.append(
                        {
                            "role": 'user', "content": self.document + '\n' + self.content,
                            'name': str(self.message.author.id)
                        })
            else:
                self.history.append({ "role": 'user', "content": self.content, 'name': str(self.message.author.id) })
            async with self.message.channel.typing():
                # async with BotThinking(channel_id=self.channel_id, content=self.content):
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
                if total_tokens >= MAX_GPT_TOKENS / 2:
                    # 使用token数超过1000给出提示
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
                if len(lines[-1] + '\n' + line) < MAX_DISCORD_TOKENS:
                    # 同时最多只处理2000个字符
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
                        'content': summary,
                    }]

                post_history += [{
                    'role'   : 'user',
                    'content': line + '\n' + self.content,
                    'name'   : str(self.message.author.id)
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

            dirname = os.path.join(DIRECTORY_OUTPUT, str(self.channel_id))
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
