import os
import time
from typing import List, Union, Optional

from loguru import logger

from game.process import Game
from agent.memory import Memory
# from agent.deepseek_azure import generate
from agent.deepseek_siliconflow import generate
# from agent.deepseek_tencent import generate
from utils.utils import *
from utils.exceptions import OutputFormatError, BrainError, TooManyRetriesError


class Player:
    def __init__(self, game: Game, player_id: int = 0):
        self.game = game
        self.id = player_id
        self.memory = Memory(self)
        self.role = None

    def __str__(self):
        return f"{self.id}号"

    def __hash__(self):
        return self.id

    def observe(self):
        return self.game.observable_state

    def __is_speaking_to_all(self, audience: List['Player']):
        alive_players = set(self.game.alive_players)
        alive_players.discard(self.game.moderator)

        audience_set = set(audience)
        audience_set.discard(self.game.moderator)
        return alive_players == audience_set

    def validate_audience(
            self,
            speaker: 'Player',
            audience: Union['Player', List['Player'], None] = None
    ) -> List['Player']:
        if audience is None:
            audience = self.game.alive_players
        elif type(audience) != list:
            audience = [audience]
        if speaker not in audience:
            audience = audience + [speaker]
        return sorted(audience, key=lambda x: x.id)

    def audience_str(
            self,
            speaker: 'Player',
            audience: List['Player']
    ):
        if self.__is_speaking_to_all(audience):
            result = "所有人"
        else:
            result = order_str(
                sorted(list(set(audience) - {speaker}), key=lambda x: x.id))
        return result

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
        output_format: type = str,
        choices: Optional[List] = None
    ):

        assert output_format in [str, int, bool]

        success = False
        attempts_remain = 10
        while not success:
            try:
                thought, content, input_messages, output = generate(prompt)

                if output_format == int:
                    parsed_content = format_int(content)
                    assert parsed_content in choices
                elif output_format == bool:
                    parsed_content = format_bool(content)
                    assert parsed_content in choices
                else:
                    parsed_content = content
                success = True
                status = 'success'

            except BrainError:
                if not attempts_remain:
                    raise TooManyRetriesError
                cooldown = 10
                logger.warning(
                    f'{self} brain malfunction, retry after {cooldown}s')
                time.sleep(cooldown)
                status = 'brain malfunction'
                attemps -= 1
            except OutputFormatError:
                logger.warning(
                    f'Wrong output format! Expected {output_format.__name__}, got "{content}"')
                status = 'wrong format'
            except AssertionError:
                logger.warning(
                    f'Choice not possible! Expected choice from {set(choices)}, got "{parsed_content}"')
                status = 'bad choice'
                
            finally:
                if status != 'brain malfunction':
                    write_jsonl_single_line(
                        data={
                            'prompt': input_messages,
                            'output': output,
                            'source': 'SiliconFlow:DeepSeek-R1-Distill-Qwen-32B',
                            'status': status
                        },
                        path=os.path.join(self.game.data_dir, 'completions.jsonl'),
                        mode='a'
                    )

        return thought, content, parsed_content

    def formulate(
        self,
        audience: List['Player'],
        output_format: type = str,
        choices: Optional[List] = None
    ):

        prompt = self.memory.retrieve()
        audience_str = self.audience_str(self, audience)
        prompt += f"\n不要忘记你的身份是{self}玩家，思考后的内容你说话的对象可以听到，直接开始说话，不要加引号。"

        assert output_format in [str, int, bool]

        if output_format == int:
            prompt += f"(output format: int)"
        elif output_format == bool:
            prompt += f"(output format: bool)"

        prompt += f"\n你对{audience_str}说："

        thought, content, parsed_content = self.generate_thought_and_content(
            prompt=prompt,
            output_format=output_format,
            choices=choices
        )

        thought = one_line_str(thought)
        self.memory.update_thought(thought)
        logger.info(f'{self} THINKS: "{thought}"')
        return thought, content, parsed_content

    def consolidate_memory(self):
        prompt = self.memory.retrieve()
        prompt += "\n结合你之前的记忆和新增信息，记录从游戏开始到现在发生的事，不要加引号。"

        _, content, _ = self.generate_thought_and_content(prompt)
        content = trim_str(content)
        self.memory.consolidate(content)
        logger.info(f'{self} CONSOLIDATES MEMORY: "{repr(content)[1:-1]}"')

    def think_and_speak(
            self,
            audience: Union['Player', List['Player'], None] = None,
            output_format: type = str,
            choices: Optional[List] = None
    ):
        audience = self.validate_audience(self, audience)
        _, content, parsed_content = self.formulate(
            audience=audience,
            output_format=output_format,
            choices=choices
        )
        self.speak(content, audience)
        return parsed_content

    def set_up_memory(self, content: str):
        self.memory.set_up(content)

    def retrieve_memory(self):
        return self.memory.retrieve()

    def select_one_player(
            self,
            abstain: bool = True
    ):
        choices = [player.id for player in self.game.alive_players]
        if abstain:
            choices += [0]
        target_id = self.think_and_speak(
            audience=self.game.moderator,
            output_format=int,
            choices=choices
        )
        target = self.game.get_player_by_id(target_id)
        logger.info(f"{self} CHOOSES: {target}")
        return target

    def decide_binary(self):
        result = self.think_and_speak(
            audience=self.game.moderator,
            output_format=bool,
            choices=[True, False]
        )
        logger.info(f"{self} DECIDES: {result}")
        return result
