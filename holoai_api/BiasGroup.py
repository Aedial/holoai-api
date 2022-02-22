from holoai_api.Preset import Model
from holoai_api.utils import tokenize_if_not

from typing import Dict, Iterable, List, Union, Any

class BiasGroup:
    _sequences: List[Union[List[int], str]]

    strength: float
    rep_pen: bool
    enabled: bool

    def __init__(self, strength: float, rep_pen: float = 1.0, enabled: bool = True):
        self._sequences = []

        self.strength = strength
        self.rep_pen = rep_pen
        self.enabled = enabled

    @classmethod
    def from_data(cls, data: Dict[str, Any]) -> "BiasGroup":
        b = cls(data["strength"], data["repPen"], data["enabled"])
        b.add(data["value"])

        return b

    def add(self, *sequences: Union[List[int], str]) -> "BiasGroup":
        for sequence in sequences:
            if type(sequence) is not str:
                assert type(sequence) is list, f"Expected type 'List[int]' for sequence, but got '{type(sequence)}'"
                for i, s in enumerate(sequence):
                    assert type(s) is int, f"Expected type 'int' for item #{i} of sequence, but got '{type(s)}: {sequence}'"

            self._sequences.append(sequence)

        return self

    def __iadd__(self, o: List[int]) -> "BiasGroup":
        self.add(o)

        return self

    def __iter__(self):
        return ({ "strength": self.strength,
                  "repPen": self.rep_pen,
                  "enabled": self.enabled,
                  "value": s } for s in self._sequences)

    def get_tokenized_biases(self, model: Model) -> Iterable[Dict[str, any]]:
        return ({ "strength": self.strength,
                  "repPen": self.rep_pen,
                  "enabled": self.enabled,
                  "value": tokenize_if_not(model, s) } for s in self._sequences)

    def __str__(self) -> str:
        return "{ " \
                    f"strength: {self.strength}, ", \
                    f"repPen: {self.rep_pen}, ", \
                    f"enabled: {self.enabled}, ", \
                    f"value: {self._sequences}" \
                " }"