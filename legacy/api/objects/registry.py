import os, sys

from api.objects.goal import Goal
from api.football import Coach, Teammate, Opponent, Target
from api.objects.bound import Bound
from api.objects.ball import Ball
from api.objects.player import Player

REGISTRY = {
    'goal': Goal,
    'coach': Coach,
    'teammate': Teammate,
    'opponent': Opponent,
    'player': Player,
    'target': Target,
    'bound': Bound,
    'ball': Ball
}

ObjectsAPI = {
    'goal': Goal,
    'coach': Coach,
    'teammate': Teammate,
    'opponent': Opponent,
    'player': Player,
    'target': Target,
    'bound': Bound,
    'ball': Ball
}