class Memory:
    def __init__(self, agent):
        self.agent = agent
        self.language = agent.language
        self.consolidated = ""
        self.cache = []

    def update_speech(self, content: str, speaker, audience: str):
        if self.language == "zh":
            you = "你"
        elif self.language == "en":
            you = "you"
        else:
            raise ValueError(f"Unsupported language: {self.language}")
        audience = audience.replace(str(self.agent), you)
        if speaker == self.agent:
            speaker = you
        else:
            speaker = str(speaker)

        self.cache.append(
            {
                "type": "speech",
                "speaker": speaker,
                "content": content,
                "audience": audience,
            }
        )

    def update_thought(self, content: str):
        self.cache.append(
            {
                "type": "thought",
                "content": content,
            }
        )

    def consolidate(self, content: str):
        self.consolidated = content
        self.cache = []

    def retrieve(self):
        if self.language == "zh":
            result = f"# 你的记忆\n\n{self.consolidated}"
            result += "\n\n# 场上状态\n{self.agent.observe()}"
            result += "\n\n# 新增信息"
            for record in self.cache:
                if record['type'] == 'speech':
                    result += f'\n{record["speaker"]}对{record["audience"]}说："{record['content']}"'
                elif record['type'] == 'thought':
                    result += f'\n你的思考："{record['content']}"'

        elif self.language == "en":
            result = f"# Your memory\n\n{self.consolidated}"
            result += "\n\n# Game state\n{self.agent.observe()}"
            result += "\n\n# New information"
            for record in self.cache:
                if record['type'] == 'speech':
                    result += f'\n{record["speaker"]} spoke to {record["audience"]}: "{record['content']}"'
                elif record['type'] == 'thought':
                    result += f'\nYour thought: "{record['content']}"'

        return result
