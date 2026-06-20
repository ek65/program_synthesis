import os, sys

class Team:
    def __init__(self, id: str = '', color: str = 'None'):
        self.id = id
        self.color = color
        self.players = []
        self.ballPosession = False
        self.goal = None