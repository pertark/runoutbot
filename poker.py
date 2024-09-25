from pokereval.card import Card
from pokereval.hand_evaluator import HandEvaluator
import random

def evaluate_hand(hand):
    return HandEvaluator.evaluate_hand(hand)

# suits = ['♠', '♥', '♦', '♣']
suits = [':spades:', ':hearts:', ':diamonds:', ':clubs:']

def card_to_str(card):
    rank = card.rank
    if rank == 14:
        rank = 'A'
    elif rank == 13:
        rank = 'K'
    elif rank == 12:
        rank = 'Q'
    elif rank == 11:
        rank = 'J'
    return "{}{}".format(rank, suits[card.suit - 1])

class Deck:
    def __init__(self):
        self.cards = []
        for suit in range(1, 5):
            for rank in range(2, 15):
                self.cards.append(Card(rank, suit))
        self.shuffle()
    def shuffle(self):
        random.shuffle(self.cards)
    
    def deal(self):
        return self.cards.pop()