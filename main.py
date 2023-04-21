import discord
from config import *
from utils import *
from group_context import GroupContext
from dm_context import DMContext
from discord import app_commands


# 如何使用斜杠命令
# https://qa.1r1g.com/sf/ask/5043065541/

# 定义bot接收到消息的事件
@bot.event
async def on_message(message: discord.Message):
    if isinstance(message.channel, discord.DMChannel):
        # 私信
        print(f'{message.author.display_name}')
        await DMContext(message).on_message()
    else:
        # 群聊
        print(f'{message.channel.name}: {message.content}')
        await GroupContext(message).on_message()


# 定义bot接收到消息编辑的事件
@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    if isinstance(after.channel, discord.DMChannel):
        # 私信
        print(f'{after.author.display_name}')
        await DMContext(after).on_message()
    else:
        # 群聊
        print(f'{after.channel.name}: {after.content}')
        await GroupContext(after).on_message()


@tree.command(name="clear", description="清空历史")
async def command_clear(interaction: discord.Interaction):
    channel_name = interaction.channel.name
    filepath = get_channel_history_path(channel_name=channel_name)
    if os.path.exists(filepath):
        os.remove(filepath)
    await interaction.response.send_message('已清空历史')


@tree.command(name="history", description="获取历史")
async def command_history(interaction: discord.Interaction):
    channel_name = interaction.channel.name
    history = get_channel_history(channel_name=channel_name)
    await discord_send_message(source=interaction, content=get_channel_history_content(history))


@tree.command(name="ask", description="提出问题，不会考虑上下文/系统，不会保存到历史")
async def command_ask(interaction: discord.Interaction, question: str):
    print('command_ask', question)
    setting = get_channel_setting(channel_id=interaction.channel.id)
    gpt_model = extract_channel_gpt_model(interaction.channel.name)
    response = get_openai_chat_completion(
            channel_name=interaction.channel.name,
            history=[{ 'role': 'user', 'content': question }],
            system=interaction.channel.topic or '',
            gpt_model=gpt_model,
            temperature=setting['temperature'])
    if isinstance(response, str):
        await discord_send_message(source=interaction, content=response)
    else:
        response_content = extract_openai_chat_response_content(response)
        await discord_send_message(source=interaction, content=response_content)


@tree.command(name="imagine", description="生成图片")
@app_commands.choices(size=[
    app_commands.Choice(name="1024", value=1024),
    app_commands.Choice(name="512", value=512),
    app_commands.Choice(name="256", value=256),
])
async def command_imagine(interaction: discord.Interaction, prompt: str, size: int = 1024):
    response = get_openai_image(prompt=prompt, width=size, height=size)
    # 生成图片
    if isinstance(response, str):
        await discord_send_message(source=interaction, content=response)
    else:
        response_content = '\n'.join([item['url'] for i, item in enumerate(response['data'])])
        await discord_send_message(source=interaction, content=response_content)
        return


@tree.command(name="temperature", description="设置GPT bot temperature")
async def command_temperature(interaction: discord.Interaction):
    # TODO 展示一些按钮或输入框来让用户配置设置
    # user_id = interaction.user.id
    channel_id = interaction.channel.id
    setting = get_channel_setting(channel_id=channel_id)
    view = discord.ui.View()

    # 获取当前的配置
    all_temperature = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8,
                       1.9,
                       2]
    temperature_options = [discord.SelectOption(label=f'{t}', value=f'{t}', default=setting['temperature'] == t) for t
                           in all_temperature]

    temperature_select = discord.ui.Select(
            placeholder=f'''**选择temperature**''',
            options=temperature_options,
            custom_id='temperature'
    )

    async def temperature_select_callback(inter: discord.Interaction):
        # TODO 获取用户选择的value
        selected_value = float(inter.data['values'][0])
        # 修改配置中的 temperature
        setting['temperature'] = selected_value
        # 保存新的配置
        save_channel_setting(channel_id=channel_id, setting=setting)
        temperature_select.options = [
            discord.SelectOption(label=f'{t}', value=f'{t}', default=setting['temperature'] == t) for t
            in all_temperature]
        await inter.response.edit_message(
                content=f'ChatGPT temperature已更新为{selected_value}',
                view=view
        )

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


# if selected_option == 'temperature':
#     # 创建一个输入框让用户输入生成文本长度
#     input_length = discord.ui.TextInput(
#             placeholder="输入文本长度",
#             min_length=1,
#             max_length=3  # 生成文本长度最长为999
#     )
#     # 编辑之前的交互式消息来替换掉刚刚的 select
#     await message.edit(components=[input_length])
# elif selected_option == 'quantity':
#     # 创建一个输入框让用户输入生成文本数量
#     input_quantity = discord.ui.TextInput(
#             placeholder="输入文本数量",
#             min_length=1,
#             max_length=3  # 生成文本数量最多为999
#     )
#     # 编辑之前的交互式消息来替换掉刚刚的 select
#     await message.edit(components=[inpu
#                                    t_quantity])
# else:
#     # 如果选择了未知的选项，发送一条提醒
#     await inter.response.send_message('未知的选项', ephemeral=True)

# 定义bot登陆事件
@bot.event
async def on_ready():
    await tree.sync()
    print('Logged in as {0.user}'.format(bot))
    for guild in bot.guilds:
        for channel in guild.text_channels:
            # if channel.name == '欢迎光临！':
            # await channel.send('我上线啦')
            print(channel)


if __name__ == '__main__':
    bot.run(os.getenv("DISCORD_STORY_BOT_TOKEN"))
