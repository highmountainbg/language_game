class Memory:
    def __init__(self, agent):
        self.agent = agent
        self.consolidated = ""
        self.cache = []

    def update_speech(self, content: str, speaker, audience: str):
        audience = audience.replace(str(self.agent), "你")
        if speaker == self.agent:
            speaker = "你"
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
        result = '# 你的记忆\n"""\n' + self.consolidated + '\n"""'
        result += "\n\n# 场上状态\n" + self.agent.observe()
        result += "\n\n# 新增信息\n"
        for record in self.cache:
            if record['type'] == 'speech':
                result += f'{record["speaker"]}对{record["audience"]}说："{record['content']}"' + "\n"
            elif record['type'] == 'thought':
                result += f'你的思考："{record['content']}"' + "\n"
        return result
