WEREWOLF_GAME_NAME = "狼人杀"

WEREWOLF_INFO = """你正在玩一个游戏，游戏名称是狼人杀。

# 游戏规则

游戏开始前，每个玩家会被分配一个角色，也都不知道其他玩家的角色。游戏开始后，分为两个阶段，交替进行。
- 夜晚
在夜晚，所有玩家都会睡去（睡眠过程中不知道是否有人行动、何人行动、如何行动）。
狼人会在裁判的指示下醒来并暗中商量，秘密投票选出一个玩家杀死，然后睡去。
如果有能在夜晚行动的角色，也会在裁判的指示下醒来行动，然后睡去。
所有能在夜间行动的玩家都行动过后，进入白天阶段。
- 白天
在白天，所有人都会醒来，裁判会宣告是否有人死亡、何人死亡，各玩家可以发言一次，最终投票选出一名玩家处决，然后进入夜晚。

## 游戏目标
在有人死亡时进行判定，如果没有狼人存活，村民获胜；如果没有村民存活，狼人获胜。

## 角色介绍
狼人：夜间可以醒来讨论，并选择一人杀死，互相知道角色身份。
平民：普通村民，没有任何特殊能力，夜间不会醒来。
预言家：有特殊能力的村民，夜间可以醒来，查看一个玩的阵营（村民或狼人）。
女巫：有特殊能力的村民，有一瓶解药和一瓶毒药，解药可以救治一个当晚被狼人击杀的玩家，毒药可以毒死一个玩家。夜间可以醒来，决定是否要使用解药或毒药，以及对谁使用。
猎人：有特殊能力的村民，被狼人击杀或投票处决时可以开枪击杀一个玩家。

## 其他规则
讨论时按升序依次发言。
投票时所有玩家同时投票，不知道别人投了什么，但投票完成后裁判会公布每个人的票。
如果得票最高的超过一人，当轮投票没有结果，无事发生，游戏进入下一个环节。
夜晚行动的顺序依次为预言家、狼人、女巫。
女巫的毒药和解药只能各使用一次。如果解药没有被用掉，女巫会在夜间醒来时被告知今晚谁被狼人杀死，并决定是否要救治，用过解药后就不会被告知。
女巫的毒药和解药不能在同一晚使用。
猎人被女巫毒死不能开枪。
如果最后只剩狼人和女巫，或狼人和猎人，互相杀死对方，算作狼人队获胜。
"""
