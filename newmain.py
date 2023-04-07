import discord
import os
import openai
import asyncio
import time

recentMessages = []

client = discord.Client(intents=discord.Intents.all())

openai.api_key = os.getenv("OPENAI_API_KEY")

gptRole = {"role": "system", "content": "You're a helpful assistant."}


#定义bot登陆事件
@client.event
async def on_ready():
    print('Logged in as {0.user}'.format(client))
    recentMessages.append(gptRole)
    #会话周期是10min，超过10min不回复则直接清空大脑
    client.loop.create_task(check_for_inactive_channel())


#定义bot接受到消息的事件
@client.event
async def on_message(message):
    global recentMessages
    global gptRole
    #不管是谁发的，都执行：
    #当对话总数超过24条，则从旧到新开始忘记
    if len(recentMessages) == 50:
        recentMessages.pop(1)

    #如果是bot发的消息
    if message.author == client.user:
        recentMessages.append({
            "role": "assistant",
            "content": message.content
        })

    #如果是用户发的消息，我就把它记到上下文里，如果包含assign，则将role设置为system
    if message.author != client.user:
        # TODO
        pass


#会话周期是10min，超过10min不回复则直接清空大脑
async def check_for_inactive_channel():
    # TODO
    pass


async def assgin_gpt_roles(gptRole):
    global recentMessages
    if len(recentMessages) > 0:
        recentMessages = [gptRole]


client.run(os.getenv("DISCORD_STORY_BOT_TOKEN"))
