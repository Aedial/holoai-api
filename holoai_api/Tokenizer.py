from os.path import abspath, dirname, join, split

from holoai_api.types import Model

from typing import List, Union

tokenizers_path = join(dirname(abspath(__file__)), "tokenizers")

class Tokenizer:
    """
    Simple lazy initialization of the tokenizer as it is heavy
    """

    _tokenizer_name = {
        Model.Model_6B: "gpt2",
        Model.Model_13B: "gpt2",
        Model.Model_20B: join(tokenizers_path, "gpt-neox"),
    }

    _tokenizer_base = {
        "gpt2": "GPT2TokenizerFast",
        "gpt-neox": "GPT2TokenizerFast"
    }

    _tokenizer = { }
    
    @classmethod
    def get_tokenizer_name(cls, model: Model) -> str:
        assert model in cls._tokenizer_name, f"Model {model} is not supported"

        return split(cls._tokenizer_name[model])[-1]

    @classmethod
    def _get_tokenizer(cls, model: Model) -> "PreTrainedTokenizerFast":
        tokenizer_name = cls.get_tokenizer_name(model)

        if tokenizer_name not in cls._tokenizer:
            import transformers

            assert tokenizer_name in cls._tokenizer_base
            TokenizerBase = getattr(transformers, cls._tokenizer_base[tokenizer_name])
            cls._tokenizer[tokenizer_name] = TokenizerBase.from_pretrained(cls._tokenizer_name[model])

        return cls._tokenizer[tokenizer_name]

    @classmethod
    def decode(cls, model: Model, o: List[int]) -> str:
        tokenizer = cls._get_tokenizer(model)

        return tokenizer.decode(o, verbose = False)

    @classmethod
    def encode(cls, model: Model, o: str) -> List[int]:
        tokenizer = cls._get_tokenizer(model)

        return tokenizer.encode(o, verbose = False)

    @classmethod
    def tokenize_if_not(model: Model, o: Union[str, List[int]]) -> List[int]:
        if type(o) is list:
            return o

        assert type(o) is str
        return Tokenizer.encode(model, o)