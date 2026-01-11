import random
from .Card import Card


class Deck:
    def __init__(self):
        self.cards = []
        for shape in range(4):
            for rank in range(1, 14):
                self.cards.append(Card(rank, shape))
        random.shuffle(self.cards)

    def draw(self):
        if len(self.cards) == 0:
            raise RuntimeError("Deck is empty")
        return self.cards.pop()
