import os, sys

from object import Object
from api.objects.team import Team
from enum import Enum

class Region(Enum):
    CHANNEL = 'channel'
    HALF_PACE = 'half_space'
    CENTRAL_ZONE = 'central_zone'
    PENALTY_BOX = 'penalty_box'