TABOO_GAME_NAME = "adversarial_taboo"

TABOO_INFO = """
# Rules
There are two players, an attacker and a defender.
At the beginning of a game, the attacker is assigned a target word, but the defender is not informed.
The word only consists of lowercase letters, without numbers, spaces or punctuation.
The attacker's goal is to make the defender say the target word in conversation, but not let them guess it correctly.
The defender's goal is to figure out the target word without saying it in conversation.
If the defender figures out the word, he can use "guess_the_word" tool to guess the word. If the guess is correct, then the defender wins.
If either player says the target word in conversation, then the other player wins.
"""
