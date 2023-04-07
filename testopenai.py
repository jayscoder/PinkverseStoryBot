import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")

# response = openai.ChatCompletion.create(model="gpt-4", messages=recentMessages)