class Hand:
    def __init__(self):
        self.cards = []

    def add_card(self, card):
        self.cards.append(card)

    def total(self):
        total = 0
        for card in self.cards:
            total += card.value()
        return total

    def is_bust(self):
        return self.total() > 21

    def __str__(self):
        result = []
        for card in self.cards:
            result.append(str(card))
        return ", ".join(result)