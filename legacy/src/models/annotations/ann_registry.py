from annotations.point import PointReference
from annotations.reference import Reference
from annotations.passing import Passing

REGISTRY = {
    'Point': PointReference,
    'Reference': Reference,
    'Pass': Passing,
    'Through Pass': Passing
}