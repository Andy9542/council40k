# warhammer_council_full.py
import os
import json
import openai
from dotenv import load_dotenv

load_dotenv()

# читаем ключ из переменной окружения,
# чтобы не хранить секрет в файле
openai.api_key = os.environ["OPENAI_API_KEY"]


# ────────────────────────────────────────
#  УТИЛИТЫ
# ────────────────────────────────────────
def token_len(history: list) -> int:
    """
    На глаз оцениваем «вес» истории: 1 токен ~ 4 символам (грубо).
    Для контроля длины контекста этой прикидки достаточно.
    """
    return sum(len(msg.get("content", "")) for msg in history) // 4


# ────────────────────────────────────────
#  БАЗОВЫЙ АГЕНТ
# ────────────────────────────────────────
class Agent:
    def __init__(self, name: str, persona: str):
        self.name = name
        self.persona = persona

    # «сырой» вызов LLM
    def _chat_completion(self, messages: list, max_tokens: int = 220) -> str:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.8,
        )
        return response.choices[0].message.content.strip()

    # обычная реплика персонажа
    def generate(self, history: list, summary: str, reply_to: str) -> str:
        messages = [
            {
                "role": "system",
                "content": (
                    f"Ты — {self.persona}. Стиль речи: Warhammer 40 000. "
                    f"Сначала обратись к {reply_to}, затем выскажи мысль."
                ),
            },
            {"role": "system", "content": f"Краткий конспект обсуждения:\n{summary}"},
        ]

        # добавляем «живой контекст» — последние 4 сообщения
        for msg in history[-4:]:
            role = msg["role"]
            # API допускает name у 'assistant' и 'user'
            content = f"{msg['name']}: {msg['content']}"
            messages.append({"role": role, "content": content})

        # заставляем модель продолжить именно за нужного персонажа
        messages.append({"role": "user", "content": f"{self.name}:"})

        return self._chat_completion(messages)

    # метод, который нужен только для SummarizerAgent
    def generate_raw(self, prompt: str) -> str:
        messages = [{"role": "user", "content": prompt}]
        return self._chat_completion(messages, max_tokens=120)


# ────────────────────────────────────────
#  СЕКРЕТАРЬ-СУММАРИЗАТОР
# ────────────────────────────────────────
class SummarizerAgent(Agent):
    def summarize(self, history_chunk: list, prev_summary: str = "") -> str:
        prompt = (
            "Ниже — предыдущий конспект (если был) и новые реплики.\n\n"
            f"=== Предыдущий конспект ===\n{prev_summary}\n\n"
            "=== Новые реплики ===\n"
            + "\n".join(f"{m['name']}: {m['content']}" for m in history_chunk)
            + "\n\nСделай новый конспект (максимум 100 слов)."
        )
        return self.generate_raw(prompt)


# ────────────────────────────────────────
#  ХРАНИЛИЩЕ ИСТОРИИ
# ────────────────────────────────────────
class ChatMemory:
    def __init__(self, filepath: str = "wh40k_history.json"):
        self.filepath = filepath

    def save_history(self, conversation_history: list):
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(conversation_history, f, ensure_ascii=False, indent=4)

    def load_history(self) -> list:
        if os.path.exists(self.filepath):
            with open(self.filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        return []


# ────────────────────────────────────────
#  ОРКЕСТРАТОР
# ────────────────────────────────────────
class ChatCouncil:
    def __init__(
        self,
        agents: list[Agent],
        memory: ChatMemory,
        summarizer: SummarizerAgent,
        rounds: int = 2,
    ):
        self.agents = agents
        self.memory = memory
        self.summarizer = summarizer
        self.rounds = rounds

        self.history = memory.load_history()
        self.summary = ""  # глобальный tl;dr

    # добавляет сообщение в историю
    def _add(self, role: str, speaker: str, content: str):
        # Сохраняем имя говорящего в контенте для сохранения совместимости
        message_content = f"{speaker}: {content}" if role == "assistant" else content
        entry = {"role": role, "content": message_content}
        # Для внутреннего использования дополнительно храним имя говорящего
        entry["name"] = speaker
        self.history.append(entry)

    # надо ли обновить summary?
    def _need_update_summary(self) -> bool:
        return len(self.history) % 10 == 0 or token_len(self.history) > 2500

    # главный метод дискуссии
    def discuss(self, user_topic: str):
        self._add("user", "Пользователь", user_topic)

        if self._need_update_summary():
            # берём свежие реплики для резюме
            new_chunk = self.history[-12:]
            self.summary = self.summarizer.summarize(new_chunk, self.summary)

        # N внутренних раундов
        for _ in range(self.rounds):
            for agent in self.agents:
                last_speaker = self.history[-1]["name"]
                answer = agent.generate(self.history, self.summary, last_speaker)
                print(f"{agent.name}: {answer}\n")
                self._add("assistant", agent.name, answer)

        self.memory.save_history(self.history)


# ────────────────────────────────────────
#  ЗАПУСК
# ────────────────────────────────────────
if __name__ == "__main__":
    # персонажи совета
    agents = [
        Agent(
            "Комиссар_Каин",
            "харизматичный, остроумный комиссар Империума; прикрывает трусость блестящими манёврами",
        ),
        Agent(
            "Уриель_Вентрис",
            "благородный капитан Ультрамаринов; говорит вдохновенно и строго по кодексу",
        ),
        Agent(
            "Велизарий_Коул",
            "архимагос Механикус; мыслит рационально, использует научный жаргон и данные",
        ),
        Agent(
            "Капеллан_Энгримаринов",
            "фанатичный капеллан; речь пафосная, полна религиозного пыла",
        ),
    ]

    # секретарь‑суммаризатор
    summarizer = SummarizerAgent(
        "Магос_Архивист",
        "холодный аналитик, сводит беседу в краткое техно‑резюме",
    )

    memory = ChatMemory()
    council = ChatCouncil(agents, memory, summarizer, rounds=2)

    # пример вызова
    council.discuss("Как победить орков на Армагеддоне?")
