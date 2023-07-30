from enum import Enum


class AggregateType(Enum):
    AVG = 0
    MIN = 1
    MAX = 2
    LAST = 3
    SUM = 4
