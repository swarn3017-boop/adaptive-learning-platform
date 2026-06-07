from typing import TypeVar

T = TypeVar('T', int, float)

def clamp(value: T, minimum: T, maximum: T) -> T:
    return max(min(value, maximum), minimum)
