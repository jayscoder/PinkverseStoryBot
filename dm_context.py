from utils import *
from collections import defaultdict

dm_history_dict = defaultdict(list)


class DMContext:

    def __init__(self, message: discord.Message):
        self.message = message
        self.content = message.content
        self.channel_id = message.channel.id
        self.file_path = f'./{DIRECTORY_CONTEXT}/{self.channel_id}.json'
        # 来自用户发的内容
        self.from_user = message.author != bot.user
        self.from_bot = message.author == bot.user
        self.author_name = message.author.display_name or message.author.nick or message.author.name or 'NoName'
        # 判断当前应该采用哪个gpt_model
        self.gpt_model = DEFAULT_GPT_MODEL
        self.system = f'''user是一个真实用户，他的名字叫{self.author_name}
assistant是user的人工智能助手'''
        # 加载历史数据
        self.history = []
        self.load_history()

    def load_history(self):
        self.history = dm_history_dict[self.channel_id]

    def dump_history(self):
        dm_history_dict[self.channel_id] = self.history

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

    # 截断历史，返回值：是否截断了
    def cut_off_history(self, max_tokens) -> bool:
        # 只保留最近N条消息，这N条消息的字符总数不能超过MAX_TOKENS
        max_tokens -= len(self.system)  # 要预留出system的空间
        temp_history = []
        temp_history_tokens = 0
        is_cut_off = False

        # 从最后一条消息开始遍历，只保留2000个字符
        for i in range(len(self.history) - 1, -1, -1):
            item_history = self.history[i]
            item_history['content'] = item_history['content'][:max_tokens]
            temp_history_tokens += len(item_history['content'])
            if temp_history_tokens > max_tokens:
                is_cut_off = True
                break
            temp_history.insert(0, item_history)
        self.history = temp_history
        self.dump_history()
        return is_cut_off

    # 获取当前历史token
    def history_tokens(self):
        tokens = 0
        for item in self.history:
            tokens += len(item['content'])
        return tokens + len(self.system)

    # on_message事件
    async def on_message(self):
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

        summary = Command.check_equal(self.content, Command.SUMMARY)
        if summary:
            self.content = '请帮我将目前给你的上下文梳理成简短的几句话'

        # 如果是system命令
        if Command.check_equal(self.content, Command.SYSTEM):
            await self.send_message(self.system)
            return

        if Command.check_startswith(self.content, Command.TOKEN):
            self.content = Command.remove_startswith(self.content, Command.TOKEN)
            tokens = self.history_tokens() + len(self.content)
            await self.send_message(
                    f'当前上下文token数: {tokens}\nGPT-4约花费{GPT_4_TOKEN_PRICE * tokens}人民币\nGPT-3.5约花费{GPT_3_5_TOKEN_PRICE * tokens}人民币\n当前使用的模型: {self.gpt_model}'
            )
            return

        if self.from_user:
            # 用户发的普通内容

            # 如果消息包含附件
            if self.message.attachments:
                for attachment in self.message.attachments:
                    # 下载附件，处理附件的字节数据
                    file_data = await attachment.read()
                    # 如果需要读取文件的内容，请确保文件是可阅读的文本类型
                    self.content += '\n' + file_data.decode("utf-8")

            self.history.append({ "role": 'user', "content": self.content })

        is_cut_off = self.cut_off_history(max_tokens=MAX_GPT_TOKENS)
        if is_cut_off:
            await self.send_message(
                    f"您上下文内容超过{MAX_GPT_TOKENS}个字符，将对其进行截断")

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

        async with self.message.channel.typing():
            response = await self.get_openai_chat_completion()

        if isinstance(response, str):
            await self.send_message(response)
        elif len(response.choices) > 0:
            if summary:
                # 归纳整理
                self.history = []

            response_content = '\n\n'.join(
                    [choice.message.content or 'None' for choice in response.choices])
            for choice in response.choices:
                self.history.append(choice.message)

            completion_tokens = response['usage']['completion_tokens']
            prompt_tokens = response['usage']['prompt_tokens']
            total_tokens = response['usage']['total_tokens']
            current_model = response['model']

            if total_tokens > MAX_GPT_TOKENS:
                response_content += f'''
    > tokens: {completion_tokens} + {prompt_tokens} = {total_tokens}
    > model: {current_model}
    > GPT-3.5: {total_tokens * GPT_3_5_TOKEN_PRICE}
    > GPT-4: ¥{total_tokens * GPT_4_TOKEN_PRICE}'''

            self.dump_history()
            await self.send_message(response_content)
        else:
            await self.send_message("ChatGPT API没有返回有效的响应。")

    async def get_openai_chat_completion(self):
        return await get_openai_chat_completion(
                channel_id=self.channel_id,
                history=self.history,
                system=self.system,
                save_data=False
        )

    async def get_openai_image(self, width: int, height: int):
        return await get_openai_image(prompt=self.content, width=width, height=height)
