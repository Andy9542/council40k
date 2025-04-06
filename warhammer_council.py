from openai import OpenAI
import json
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class Agent:
    def __init__(self, name, persona):
        self.name = name
        self.persona = persona

    def generate_response(self, history):
        dialog_text = ""
        for msg in history:
            dialog_text += f"{msg['speaker']}: {msg['message']}\n"
        dialog_text += f"{self.name}:"

        messages = [
            {"role": "system", "content": f"Ты ведёшь себя как персонаж из Warhammer 40,000: {self.persona}"},
            {"role": "user", "content": dialog_text}
        ]
        response = client.chat.completions.create(model="gpt-4o",
        messages=messages,
        max_tokens=250,
        temperature=0.7)
        reply = response.choices[0].message.content.strip()
        return reply

class ChatMemory:
    def __init__(self, filepath="wh40k_history.json"):
        self.filepath = filepath

    def save_history(self, conversation_history):
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(conversation_history, f, ensure_ascii=False, indent=4)

    def load_history(self):
        if os.path.exists(self.filepath):
            with open(self.filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

class ChatCouncil:
    def __init__(self, agents, memory):
        self.agents = agents
        self.memory = memory
        self.history = self.memory.load_history()
        if self.history:
            print("История диалога загружена. Продолжим дискуссию!\n")
        else:
            print("Начинаем новый совет Вархаммер 40k персонажей.\n")

    def add_user_message(self, message):
        self.history.append({"speaker": "Пользователь", "message": message})

    def generate_responses(self):
        for agent in self.agents:
            response = agent.generate_response(self.history)
            print(f"{agent.name}: {response}\n")
            self.history.append({"speaker": agent.name, "message": response})
        self.memory.save_history(self.history)

if __name__ == "__main__":
    # Создание агентов с описаниями личностей
    agents = [
        Agent("Комиссар Каин", "знаменитый герой Империума, харизматичный и остроумный комиссар, хитрый, всегда скрывает истинные намерения под шутками и иронией"),
        Agent("Уриель Вентрис", "благородный и верный капитан Ультрамаринов, всегда дисциплинирован, говорит гордо, чётко и вдохновляюще, воплощает честь и достоинство ордена"),
        Agent("Велизарий Коул", "гениальный Архимагос Адептус Механикус, крайне рациональный, говорит научно и технологично, склонен к глубоким техническим рассуждениям и анализу данных"),
        Agent("Капеллан Энгримаринов", "фанатичный капеллан космодесанта, всегда эмоционально призывает к вере в Императора, говорит в пафосной и пламенной манере, полон религиозного вдохновения и решительности")
    ]

    memory = ChatMemory()
    council = ChatCouncil(agents, memory)

    while True:
        user_input = input("\nЗадай тему для обсуждения (или 'выход' для завершения): ")
        if user_input.lower() == 'выход':
            print("Завершаем обсуждение. Ave Imperator!")
            break
        council.add_user_message(user_input)
        council.generate_responses()