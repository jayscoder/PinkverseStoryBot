import utils
from utils import *
from bots import *


# 定义bot登陆事件
@magi_bot.event
async def on_ready():
    await magi_bot_tree.sync()
    print('Magi Logged in as {0.user}'.format(magi_bot))
    # for guild in magi_bot.guilds:
    #     for channel in guild.text_channels:
    #         # if channel.name == '欢迎光临！':
    #         # await channel.send('我上线啦')
    #         print(channel)
    #         # asyncio.create_task(save_channel_info(channel))


# 如何使用斜杠命令
# https://qa.1r1g.com/sf/ask/5043065541/


# 定义bot接收到消息的事件
@magi_bot.event
async def on_message(message: discord.Message):
    if check_is_mention_cooper(message) and not check_is_mention_magi(message):
        # 提到了Cooper且没有提到Magi，不再回复
        return

    # 群聊
    print(f'Magi {message.author.display_name}: {message.content}')
    await MagiChannelContext(message).on_message()
    asyncio.create_task(save_channel_info(message.channel))

    # await save_channel_info(message.channel)

    # if isinstance(message.channel, discord.DMChannel):
    #     # 私信
    #     print(f'{message.author.display_name}')
    #     await DMContext(message).on_message()
    # else:
    #     # 群聊
    #     print(f'{message.channel.name}: {message.content}')
    #     await GroupContext(message).on_message()


# 定义bot接收到消息编辑的事件
@magi_bot.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    print(f'{after.author.display_name}: {after.content}')
    await MagiChannelContext(after, bot=magi_bot).on_message()
    # if isinstance(after.channel, discord.DMChannel):
    #     # 私信
    #     print(f'{after.author.display_name}')
    #     await DMContext(after).on_message()
    # else:
    #     # 群聊
    #     print(f'{after.channel.name}: {after.content}')
    #     await GroupContext(after).on_message()


@magi_bot_tree.command(name="clear", description="清除历史")
@app_commands.describe(reserve='保留多少历史项，正数表示从后往前保留，负数表示从前往后保留')
async def command_clear(interaction: discord.Interaction, reserve: int = 0):
    history = utils.get_channel_context(channel_id=interaction.channel.id)
    old_history_count = len(history)
    history = clear_history_by_reserve(history, reserve=reserve)

    utils.save_channel_context(channel_id=interaction.channel.id, history=history)
    if reserve > 0:
        await interaction.response.send_message(
                f'已清除{old_history_count - len(history)}项历史，并保留了后{len(history)}项')
    elif reserve < 0:
        await interaction.response.send_message(
                f'已清除{old_history_count - len(history)}项历史，并保留了前{len(history)}项')
    else:
        await interaction.response.send_message(f'已清除{old_history_count - len(history)}项历史')


@magi_bot_tree.command(name="history", description="获取历史")
async def command_history(interaction: discord.Interaction):
    history = get_channel_context(channel_id=interaction.channel.id)
    await discord_send_message(source=interaction,
                               content=convert_channel_history_to_content(history))


@magi_bot_tree.command(name="current-model", description="获取当前使用的GPT模型")
async def command_current_model(interaction: discord.Interaction):
    model = extract_channel_gpt_model(channel_name=extract_channel_name(channel=interaction.channel))
    await discord_send_message(source=interaction,
                               content=model)


# @tree.command(name="list models", description="获取当前可以使用的GPT模型列表")
# async def command_list_models(interaction: discord.Interaction):
#     model = extract_channel_gpt_model(channel_name=extract_channel_name(channel=interaction.channel))
#     await discord_send_message(source=interaction,
#                                content=model)

@magi_bot_tree.command(name="survey", description="让Cooper替你自动调研某个主题")
@app_commands.choices(model=[
    app_commands.Choice(name="gpt-3.5", value=GPT_MODEL_3_5),
    app_commands.Choice(name="gpt-4", value=GPT_MODEL_4),
])
@app_commands.describe(subject="主题", question_count="问答次数", model='GPT模型')
async def command_survey(interaction: discord.Interaction, subject: str, question_count: int = 10,
                         model: str = GPT_MODEL_3_5):
    await discord_send_message(source=interaction, content=f'{subject} --question_count={question_count} model={model}')

    setting = get_channel_setting(channel_id=interaction.channel.id)
    temperature = setting['temperature']

    content = f'请详细介绍一下 "{subject}"'
    await discord_send_message(source=cooper_dog.get_channel(interaction.channel.id), content=content)

    async with interaction.channel.typing():
        response = await get_openai_chat_completion(
                channel_id=interaction.channel.id,
                history=[{ 'role': 'user', 'content': content }],
                system=f'你是一个"{subject}"专家',
                gpt_model=model,
                temperature=temperature)

    if isinstance(response, str):
        await discord_send_message(source=interaction.channel, content=response)
        return

    subject_intro = extract_openai_chat_response_content(response)
    await discord_send_message(source=interaction.channel,
                               content=subject_intro)

    content = f'关于“{subject}”，请你从不同的角度或关联的领域，提出{question_count}个我可能感兴趣的问题（要帮助我快速了解这个主题）:'
    await discord_send_message(source=cooper_dog.get_channel(interaction.channel.id), content=content)

    async with interaction.channel.typing():
        response = await get_openai_chat_completion(
                channel_id=interaction.channel.id,
                history=[{ 'role': 'user', 'content': content }],
                system=subject_intro,
                gpt_model=model,
                temperature=temperature)

    if isinstance(response, str):
        await discord_send_message(source=interaction.channel, content=response)
        return

    question_content = extract_openai_chat_response_content(response)
    await discord_send_message(source=interaction.channel,
                               content=question_content)

    questions = question_content.split('\n')
    for question in questions:
        question = question.strip()
        if question == '':
            continue
        if not question[0].isdigit():
            continue

        await discord_send_message(
                source=cooper_dog.get_channel(interaction.channel.id),
                content=question)

        async with interaction.channel.typing():
            response = await get_openai_chat_completion(
                    channel_id=interaction.channel.id,
                    history=[{ 'role': 'user', 'content': question }],
                    system=subject_intro,
                    gpt_model=model,
                    temperature=temperature)

        if isinstance(response, str):
            await discord_send_message(source=interaction.channel, content=response)
            return
        response_content = extract_openai_chat_response_content(response)
        await discord_send_message(source=interaction.channel,
                                   content=response_content)


@magi_bot_tree.command(name="ask", description="提出问题，不考虑系统")
@app_commands.choices(model=[
    app_commands.Choice(name="gpt-3.5", value=GPT_MODEL_3_5),
    app_commands.Choice(name="gpt-4", value=GPT_MODEL_4),
])
@app_commands.describe(question='问题', model='GPT模型')
async def command_ask(interaction: discord.Interaction, question: str, model: str = GPT_MODEL_3_5):
    if len(question) == 0:
        await discord_send_message(source=interaction, content='问题不能为空')
        return

    setting = get_channel_setting(channel_id=interaction.channel.id)
    temperature = setting['temperature']
    await discord_send_message(source=interaction,
                               content=f'> {question} --model={model} --temperature={temperature}')
    history = get_channel_context(channel_id=interaction.channel.id)
    history.append({
        'role'   : 'user',
        'content': question
    })

    async with interaction.channel.typing():
        response = await get_openai_chat_completion(
                channel_id=interaction.channel.id,
                history=history,
                system='',
                gpt_model=model,
                temperature=temperature)
    if isinstance(response, str):
        await discord_send_message(source=interaction.channel, content=response)
    else:
        response_content = extract_openai_chat_response_content(response)
        history.append({
            'role'   : 'assistant',
            'content': response_content,
        })
        save_channel_context(channel_id=interaction.channel.id, history=history)
        await discord_send_message(source=interaction.channel,
                                   content=response_content)


@magi_bot_tree.command(name="repeat", description="让Cooper替你重复向Magi提问")
@app_commands.choices(model=[
    app_commands.Choice(name="gpt-3.5", value=GPT_MODEL_3_5),
    app_commands.Choice(name="gpt-4", value=GPT_MODEL_4),
])
@app_commands.describe(content='重复的提问', count='重复次数', model='GPT模型',
                       reserve_history='保留多少历史项，正数表示从后往前保留，负数表示从前往后保留')
async def command_repeat(
        interaction: discord.Interaction,
        content: str,
        count: int,
        model: str = GPT_MODEL_3_5,
        reserve_history: int = 7):
    if len(content) == 0:
        await discord_send_message(source=interaction, content='内容不能为空')
        return

    setting = get_channel_setting(channel_id=interaction.channel.id)
    temperature = setting['temperature']

    await discord_send_message(source=interaction,
                               content=f'> {content} --count={count} --model={model} --reserve_history={reserve_history} --temperature={temperature}')

    system = extract_channel_topic(interaction.channel)
    history = get_channel_context(channel_id=interaction.channel.id)

    for i in range(count):
        history.append({
            'role'   : 'user',
            'content': content
        })

        await discord_send_message(
                source=cooper_dog.get_channel(interaction.channel.id),
                content=content)

        history = clear_history_by_reserve(history, reserve=reserve_history)
        async with interaction.channel.typing():
            response = await get_openai_chat_completion(
                    channel_id=interaction.channel.id,
                    history=history,
                    system=system,
                    gpt_model=model,
                    temperature=temperature)

        if isinstance(response, str):
            await discord_send_message(source=interaction.channel, content=response)
            return

        response_content = extract_openai_chat_response_content(response)
        history.append({
            'role'   : 'assistant',
            'content': response_content,
        })
        save_channel_context(channel_id=interaction.channel.id, history=history)
        await discord_send_message(
                source=interaction.channel,
                content=response_content)


@magi_bot_tree.command(name="auto", description="让Cooper来自动替你回复，重复多次")
@app_commands.choices(model=[
    app_commands.Choice(name="gpt-3.5", value=GPT_MODEL_3_5),
    app_commands.Choice(name="gpt-4", value=GPT_MODEL_4),
])
@app_commands.describe(
        content='启动内容',
        count='重复次数',
        model='GPT模型',
        reserve_history='保留多少历史项，正数表示从后往前保留，负数表示从前往后保留',
        cooper_system='Cooper的系统'
)
async def command_auto(
        interaction: discord.Interaction,
        content: str,
        count: int,
        model: str = GPT_MODEL_3_5,
        reserve_history: int = 7,
        cooper_system: str = '',
):
    if content == '':
        await discord_send_message(source=interaction, content='内容不能为空')
        return

    setting = get_channel_setting(channel_id=interaction.channel.id)
    temperature = setting['temperature']

    await discord_send_message(source=interaction,
                               content=f'> {content} --count={count} --model={model} --temperature={temperature} --reserve_history={reserve_history} --cooper_system={cooper_system}')

    history = get_channel_context(channel_id=interaction.channel.id)
    history.append({
        'role'   : 'user',
        'content': content
    })
    cooper_channel = cooper_dog.get_channel(interaction.channel.id)
    system = extract_channel_topic(interaction.channel)

    for i in range(count):
        history = clear_history_by_reserve(history, reserve=reserve_history)

        async with interaction.channel.typing():
            response = await get_openai_chat_completion(
                    channel_id=interaction.channel.id,
                    history=history,
                    system=system,
                    gpt_model=model,
                    temperature=temperature)

        if isinstance(response, str):
            await discord_send_message(source=interaction.channel, content=response)
            return

        response_content = extract_openai_chat_response_content(response)
        history.append({
            'role'   : 'assistant',
            'content': response_content,
        })

        save_channel_context(channel_id=interaction.channel.id, history=history)
        await discord_send_message(source=interaction.channel,
                                   content=response_content)

        # Cooper模拟用户
        history_ai = []
        for h in history:
            if h['role'] == 'user':
                history_ai.append({
                    'role'   : 'assistant',
                    'content': h['content']
                })
            else:
                history_ai.append({
                    'role'   : 'user',
                    'content': h['content']
                })

        history_ai = clear_history_by_reserve(history_ai, reserve=reserve_history)

        async with cooper_channel.typing():
            response = await get_openai_chat_completion(
                    channel_id=interaction.channel.id,
                    history=history_ai,
                    system=cooper_system,
                    gpt_model=model,
                    temperature=temperature)

        if isinstance(response, str):
            await discord_send_message(source=interaction.channel, content=response)
            return

        response_content = extract_openai_chat_response_content(response)
        history.append({
            'role'   : 'user',
            'content': response_content,
        })
        save_channel_context(channel_id=interaction.channel.id, history=history)
        await discord_send_message(source=cooper_channel,
                                   content=response_content)


@magi_bot_tree.command(name="imagine", description="生成图片")
@app_commands.choices(size=[
    app_commands.Choice(name="1024", value=1024),
    app_commands.Choice(name="512", value=512),
    app_commands.Choice(name="256", value=256),
])
async def command_imagine(interaction: discord.Interaction,
                          prompt: str,
                          size: int = 1024):
    await discord_send_message(source=interaction, content=f'> {prompt} --width={size} --height={size}')
    response = await get_openai_image(prompt=prompt, width=size, height=size)

    # 生成图片（响应时间太久了就无法发送消息了）
    if isinstance(response, str):
        await discord_send_message(source=interaction.channel, content=response)
        return
    else:
        response_content = '\n'.join(
                [item['url'] for i, item in enumerate(response['data'])])
        await discord_send_message(source=interaction.channel,
                                   content=response_content)
        return


@magi_bot_tree.command(name="temperature", description="设置GPT bot temperature")
async def command_temperature(interaction: discord.Interaction):
    # TODO 展示一些按钮或输入框来让用户配置设置
    # user_id = interaction.user.id
    channel_id = interaction.channel.id
    setting = get_channel_setting(channel_id=channel_id)
    view = discord.ui.View()

    # 获取当前的配置
    all_temperature = [
        0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1, 1.1, 1.2, 1.3, 1.4,
        1.5, 1.6, 1.7, 1.8, 1.9, 2
    ]
    temperature_options = [
        discord.SelectOption(label=f'{t}',
                             value=f'{t}',
                             default=setting['temperature'] == t)
        for t in all_temperature
    ]

    temperature_select = discord.ui.Select(
            placeholder=f'''**选择temperature**''',
            options=temperature_options,
            custom_id='temperature')

    async def temperature_select_callback(inter: discord.Interaction):
        # TODO 获取用户选择的value
        selected_value = float(inter.data['values'][0])
        # 修改配置中的 temperature
        setting['temperature'] = selected_value
        # 保存新的配置
        save_channel_setting(channel_id=channel_id, setting=setting)
        temperature_select.options = [
            discord.SelectOption(label=f'{t}',
                                 value=f'{t}',
                                 default=setting['temperature'] == t)
            for t in all_temperature
        ]
        await inter.response.edit_message(
                content=f'ChatGPT temperature已更新为{selected_value}', view=view)

    temperature_select.callback = temperature_select_callback

    view.add_item(temperature_select)

    await interaction.response.send_message(
            f'''**选择temperature**
What sampling temperature to use, between 0 and 2. Higher values like 0.8 will make the output more random, while lower values like 0.2 will make it more focused and deterministic.
We generally recommend altering this or top_p but not both.''',
            view=view,
    )

    # 创建一个 select 交互式消息组件来让用户选择设置
    # select = discord.ui.Button(
    #         label=f"temperature={setting['temperature']}",
    #         custom_id='temperature',
    #         description='What sampling temperature to use, between 0 and 2. Higher values like 0.8 will make the output more random, while lower values like 0.2 will make it more focused and deterministic'),
    # )
    #
    # # 创建一个交互式消息，包含上面的 select
    # message = await interaction.response.send_message(
    #         '选择你要配置的设置',
    #         components=[select],
    #         # ephemeral=True  # 只有用户能看到这个消息
    # )

    # 创建响应 select 输入的方法
    # async def callback(inter: discord.Interaction):
    #     selected_option = inter.data['custom_id']
    #     # 根据用户选择的设置，展示相应的输入框或按钮
    #     if selected_option == 'temperature':
    #         # 创建一个 select 交互式消息组件来让用户选择 GPT 模型
    #
    #         # 编辑之前的交互式消息来替换掉刚刚的 select
    #         await message.edit(components=[select_temperature])
    #     # TODO 处理一下用户点击了


# 频道上下文
class MagiChannelContext:

    def __init__(self, message: discord.Message):
        self.message = message
        self.content = message.content
        self.channel_name = extract_channel_name(message.channel)
        self.channel = message.channel
        self.channel_id = message.channel.id
        # 来自用户发的内容
        self.from_user = message.author != magi_bot.user and message.author != cooper_dog.user
        self.from_magi = message.author == magi_bot.user
        self.from_dog = message.author == cooper_dog.user

        self.document = ''  # 文档里的内容
        self.setting = get_channel_setting(channel_id=message.channel.id)
        self.author_name = message.author.display_name or message.author.nick or message.author.name
        self.author_id = message.author.id
        print(f'channel_id={self.channel_id} author_id={self.author_id}')
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

        self.system = extract_channel_topic(channel=message.channel)
        if self.system == '':
            if self.channel_mode & ChannelMode.GROUP:
                self.system = DEFAULT_GROUP_GPT_SYSTEM
            else:
                self.system = DEFAULT_GPT_SYSTEM
        if isinstance(message.channel, DMChannel):
            self.system = f'''user是一个真实用户，他的名字叫{self.author_name}
            assistant是user的人工智能助手'''

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
        await discord_send_message(source=self.channel, content=content)

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
        if self.from_dog:
            # 狗发的话直接跳过
            return

        if self.channel_mode & ChannelMode.GROUP:
            # 群模式下需要添加群成员列表
            self.system += '\n群成员列表:\n' + '\n'.join(await
                                                         get_channel_member_list(channel=self.channel))

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
            member_list = await get_channel_member_list(channel=self.channel)
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
            if self.channel_mode & ChannelMode.GROUP:
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

        if self.from_magi or self.from_dog:
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
