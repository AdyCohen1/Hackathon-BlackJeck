Shape = ["Heart", "Diamond", "Club", "Spade"]


class Card:
    def __init__(self, rank, shape):
        if not (1 <= rank <= 13):
            raise ValueError("Invalid rank")
        if not (0 <= shape <= 3):
            raise ValueError("Invalid suit")
        self.rank = rank
        self.shape = shape

    def value(self):
        if self.rank == 1:
            return 11
        if self.rank >= 10:
            return 10
        return self.rank

    def __str__(self):
        if self.rank == 1:
            rank_str = "A"
        elif self.rank == 11:
            rank_str = "J"
        elif self.rank == 12:
            rank_str = "Q"
        elif self.rank == 13:
            rank_str = "K"
        else:
            rank_str = str(self.rank)

        return f"{rank_str} of {Shape[self.shape]}"
