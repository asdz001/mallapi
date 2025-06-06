from typing_extensions import LiteralString, Self

def RecurrenceOperators(base, generator) -> tuple[RecurrenceOperatorAlgebra, RecurrenceOperator]: ...

class RecurrenceOperatorAlgebra:
    def __init__(self, base, generator) -> None: ...

    __repr__ = ...
    def __eq__(self, other) -> bool: ...

class RecurrenceOperator:
    _op_priority = ...
    def __init__(self, list_of_poly, parent) -> None: ...
    def __mul__(self, other) -> RecurrenceOperator: ...
    def __rmul__(self, other) -> RecurrenceOperator | None: ...
    def __add__(self, other) -> RecurrenceOperator: ...

    __radd__ = ...
    def __sub__(self, other): ...
    def __rsub__(self, other): ...
    def __pow__(self, n) -> Self | RecurrenceOperator | None: ...

    __repr__ = ...
    def __eq__(self, other) -> bool: ...

class HolonomicSequence:
    def __init__(self, recurrence, u0=...) -> None: ...
    def __repr__(self) -> LiteralString: ...

    __str__ = ...
    def __eq__(self, other) -> bool: ...
