import os
import random
import time
from typing import List, Union, Optional

from loguru import logger

from game import Game
from utils.utils import (
    order_str,
    one_line_str,
    write_jsonl_single_line,
    unique_identifier,
)
from utils.exceptions import (
    BadChoice,
    TooManyRetries,
    BrainMalfunction,
    InvalidToolCall,
)
from .deepseek_reasoner import (
    generate,
    MODEL
)
# from .groq_qwq import (
#     generate,
#     MODEL
# )
from .memory import Memory
from .tools import (
    Tool,
    DecideBinary,
    SelectOnePlayer,
)


class Player:
    def __init__(
            self,
            game: Game,
            player_id: int,
            tools: List[Tool] = None
    ):
        self.game = game
        self.language = self.game.language
        self.id = player_id
        self.memory = Memory(self)
        self.alive = True
        self.role = None
        self.tools = tools if tools is not None else []
        self.system = ""

    def __str__(self):
        if self.language == "zh":
            return f"{self.id}号"
        elif self.language == "en":
            return f"Player {self.id}"
        else:
            raise ValueError(f"Unsupported language: {self.language}")

    def initialize_system(
            self,
            system: str,
            include_tools: bool = False
    ):
        self.system = system
        if include_tools:
            self.system += """
# Tools


You may call one or more functions to assist with the user query.

You are provided with function signatures within <tools></tools> XML tags:
<tools>
"""
            self.system += "\n".join([str(tool()) for tool in self.tools])
            self.system += """
</tools>

For each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:
<tool_call>
{"name": <function-name>, "arguments": <args-json-object>}
</tool_call>
"""

    def observe(self):
        return self.game.observable_state

    def __is_speaking_to_all(self, audience: List['Player']):
        players = set(self.game.players)
        players.discard(self.game.moderator)

        audience_set = set(audience)
        audience_set.discard(self.game.moderator)
        return players == audience_set

    def validate_audience(
            self,
            speaker: 'Player',
            audience: Union['Player', List['Player'], None] = None
    ) -> List['Player']:
        if audience is None:
            audience = self.game.players
        elif not isinstance(audience, list):
            audience = [audience]
        if speaker not in audience:
            audience = audience + [speaker]
        return sorted(audience, key=lambda x: x.id)

    def audience_str(
            self,
            speaker: 'Player',
            audience: List['Player']
    ) -> str:
        if self.__is_speaking_to_all(audience):
            if self.language == "zh":
                return "所有人"
            elif self.language == "en":
                return "all"
            else:
                raise ValueError(f"Unsupported language: {self.language}")
        else:
            return order_str(
                sorted(list(set(audience) - {speaker}), key=lambda x: x.id))

    def speak(
            self,
            msg: str,
            audience: Union['Player', List['Player'], None] = None
    ):
        msg = one_line_str(msg)

        audience = self.validate_audience(self, audience)
        audience_str = self.audience_str(speaker=self, audience=audience)
        for player in audience:
            player.__hear(msg, self, audience_str)

        logger.info(f'{self} SPEAKS to {audience_str}: "{msg}"')

    def __hear(self, msg: str, speaker: 'Player', audience_str: str):
        self.memory.update_speech(msg, speaker, audience_str)

    def generate_thought_and_content(
        self,
        prompt: str,
        tool: Optional[Tool] = None
    ):

        success = False
        attempts_remain = 10
        messages = [
            {"role": "system", "content": self.system},
            {"role": "user", "content": prompt}
        ]
        output = None

        while not success:
            try:
                #### dummy agent brain ####
                # thought = f"test thought {unique_identifier()}"
                # if isinstance(tool, SelectOnePlayer):
                #     choices = [p.id for p in tool.choices]
                #     if tool.abstain:
                #         choices += [0]
                #     content = str(random.choice(choices))
                # elif isinstance(tool, DecideBinary):
                #     choices = [True, False]
                #     content = str(random.choice(choices))
                # else:
                #     content = f"test content {unique_identifier()}"
                # output = f"<think>\n{thought}\n</think>\n{content}"
                #### dummy agent brain ####

                #### real agent brain ####
                thought, content, output = generate(messages)
                #### real agent brain ####

                if tool is None:
                    result = content
                else:
                    result = tool.parse_result(content)

                success = True
                self.game.record_detail(
                    {
                        "curr": self.game.curr.step_str,
                        "player": self.id,
                        "role": self.role,
                        "prompt": prompt,
                        "output": output
                    }
                )

            except BrainMalfunction:
                if not attempts_remain:
                    raise TooManyRetries("Exceeded max attempts.")
                cooldown = 1
                logger.warning(
                    f'{self} brain malfunction, retry after {cooldown}s')
                time.sleep(cooldown)
                attempts_remain -= 1
            except (
                BadChoice,
                InvalidToolCall
            ) as e:
                write_jsonl_single_line(
                    data={
                        'messages': messages,
                        'output': output,
                        'source': MODEL,
                        'error': str(e)
                    },
                    path=os.path.join(self.game.data_dir,
                                      'completions.jsonl'),
                    mode='a'
                )

        return thought, content, result

    def think_and_speak(
            self,
            audience: Union['Player', List['Player'], None] = None,
            tool: Optional[Tool] = None
    ):

        audience = self.validate_audience(self, audience)
        audience_str = self.audience_str(self, audience)

        prompt = self.memory.retrieve()

        if tool is None:
            if self.language == "zh":
                prompt += f"\n你说话的对象是{audience_str}，思考后直接开始说话。"
            elif self.language == "en":
                prompt += f"\nYou are speaking to {audience_str}. Speak directly after thinking."
            else:
                raise ValueError(f"Unsupported language: {self.language}")
        else:
            prompt += f"output format: {tool.output_format.__name__}"

        thought, content, result = self.generate_thought_and_content(
            prompt=prompt,
            tool=tool
        )
        self.memory.update_thought(one_line_str(thought))
        logger.info(f'{self} THINKS: "{thought}"')

        self.speak(content, audience)
        return result

    def retrieve_memory(self):
        return self.memory.retrieve()

    def consolidate_memory(self):
        prompt = self.memory.retrieve()
        if self.language == "zh":
            prompt += "\n结合你之前的记忆和新增信息，记录从游戏开始到现在发生的事。"
        elif self.language == "en":
            prompt += "\nAccording to old memeory and new information, record what has happened in the game so far."
        else:
            raise ValueError(f"Unsupported language: {self.language}")

        _, new_memory, _ = self.generate_thought_and_content(prompt)

        self.memory.consolidate(new_memory)
        logger.info(
            f'{self} CONSOLIDATES MEMORY: "{new_memory}"')

    def select_one_player(
            self,
            choices: List["Player"] = None,
            abstain: bool = True,
    ):
        target = self.think_and_speak(
            audience=self.game.moderator,
            tool=SelectOnePlayer(choices=choices, abstain=abstain)
        )

        logger.info(f"{self} CHOOSES: {target}")
        return target

    def decide_binary(self):
        result = self.think_and_speak(
            audience=self.game.moderator,
            tool=DecideBinary()
        )

        logger.info(f"{self} DECIDES: {result}")
        return result
