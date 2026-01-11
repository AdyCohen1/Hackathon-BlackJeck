from .Deck import Deck
from .Hand import Hand


class Game:
    def __init__(self):
        self.deck = Deck()
        self.player_hand = Hand()
        self.dealer_hand = Hand()
        self.finished = False

    def start(self):
        # initial deal
        self.player_hand.add_card(self.deck.draw())
        self.dealer_hand.add_card(self.deck.draw())
        self.player_hand.add_card(self.deck.draw())
        self.dealer_hand.add_card(self.deck.draw())

    def player_hit(self):
        card = self.deck.draw()
        self.player_hand.add_card(card)

        if self.player_hand.is_bust():
            self.finished = True

        return card

    def player_stand(self):
        while self.dealer_hand.total() < 17:
            self.dealer_hand.add_card(self.deck.draw())

        self.finished = True

    def result(self):
        if self.player_hand.is_bust():
            return "loss"
        if self.dealer_hand.is_bust():
            return "win"

        if self.player_hand.total() > self.dealer_hand.total():
            return "win"
        if self.player_hand.total() < self.dealer_hand.total():
            return "loss"
        return "tie"
