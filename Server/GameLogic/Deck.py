import random
from Server.GameLogic.Card import Card


class Deck:
    def __init__(self):
        self.cards = []
        for suit in range(4):
            for rank in range(1, 14):
                self.cards.append(Card(rank, suit))
        random.shuffle(self.cards)

    def draw(self):
        if len(self.cards) == 0:
            raise RuntimeError("Deck is empty")
        return self.cards.pop()
