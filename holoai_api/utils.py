from base64 import b64encode, b64decode
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA256
from functools import partial
from json import dumps, loads

from holoai_api.types import Model
from holoai_api.Tokenizer import Tokenizer
from holoai_api.Preset import Preset
from holoai_api.BanList import BanList
from holoai_api.BiasGroup import BiasGroup

from typing import Dict, Union, List, Tuple, Any, Optional, NoReturn, TypeVar

T = TypeVar("T")

dumps = partial(dumps, separators = (',', ':'), ensure_ascii = False)
def clamp(l: T, v: T, h: T) -> T:
    return (l if v < l else h if h < v else v)

class Sjcl_ccm:
    @classmethod
    def get_key(cls, content: Dict[str, Any], account_key: bytes) -> bytes:
        salt = b64decode(content["salt"])
        key_len = content["ks"] // 8
        key_iter = content["iter"]
        return PBKDF2(account_key, salt, key_len, key_iter, hmac_hash_module = SHA256)

    # kudos to Schmitty#5079 for coming up with the way to convert iv to nonce (extracted from ccm.js in sjcl)
    @classmethod
    def get_nonce_from_iv(cls, content: Dict[str, Any], ct_len: int) -> bytes:
        iv = b64decode(content["iv"])

        # nonce = iv[0:13] down to iv[0:11] depending on ciphertext length
        nonce_size = 13 - clamp(0, (ct_len.bit_length() // 8) - 2, 2)

        return iv[:nonce_size]

    @classmethod
    def decrypt(cls, content: Dict[str, Any], account_key: bytes) -> bytes:
        ciphertext = b64decode(content["ct"])
        tag_len = content["ts"] // 8

        tag = ciphertext[-tag_len:]
        ciphertext = ciphertext[:-tag_len]

        cipher_len = len(ciphertext)
        key = cls.get_key(content, account_key)
        nonce = cls.get_nonce_from_iv(content, cipher_len)

        aes = AES.new(key, AES.MODE_CCM, nonce = nonce, mac_len = tag_len)
        cleartext = aes.decrypt_and_verify(ciphertext, tag)

        return cleartext

    @classmethod
    def encrypt(cls, content: Dict[str, Any], account_key: bytes) -> bytes:
        cleartext = content["ct"]
        tag_len = content["ts"] // 8

        if type(cleartext) is dict:
            cleartext = dumps(cleartext)

        cleartext = cleartext.encode()

        clear_len = len(cleartext)
        key = cls.get_key(content, account_key)
        nonce = cls.get_nonce_from_iv(content, clear_len)

        aes = AES.new(key, AES.MODE_CCM, nonce = nonce, mac_len = tag_len)
        ciphertext, tag = aes.encrypt_and_digest(cleartext)

        return b64encode(ciphertext + tag)

# FIXME: get proper errors ?
def decrypt_content(content: Dict[str, Any], account_key: bytes, loads_ct: Optional[bool] = False) -> NoReturn:
    cipher = content.get("cipher")
    mode = content.get("mode")
    if cipher == "aes":
        if mode == "ccm":
            cleartext = Sjcl_ccm.decrypt(content, account_key)
        else:
            RuntimeError(f"Unsupported mode for AES, expected CCM, but got {mode}")

    else:
        RuntimeError(f"Unsupported cipher, expected aes, but got {cipher}")   

    content["ct"] = cleartext.decode()
    if loads_ct:
        content["ct"] = loads(content["ct"])

    content["decrypted"] = True

def format_and_decrypt_stories(account_key: bytes, *stories: Dict[str, Any]) -> NoReturn:
    for story in stories:
        story["genSettings"]["logitBias"] = loads(story["genSettings"]["logitBias"])

        for field in ("title", "preview", "content", "description"):
            if field in story:
                if not story[field]:
                    story[field] = None
                else:
                    story[field] = loads(story[field])

                    if type(story[field]) is str:	# safer than checking story["encrypted"]
                        story[field] = loads(story[field])

                    decrypt_content(story[field], account_key, (field == "content"))

def encrypt_content(content: Dict[str, Any], account_key: bytes) -> NoReturn:
    if content.get("decrypted", False):
        cipher = content.get("cipher")
        mode = content.get("mode")
        if cipher == "aes":
            if mode == "ccm":
                cleartext = Sjcl_ccm.encrypt(content, account_key)
            else:
                RuntimeError(f"Unsupported mode for AES, expected CCM, but got {mode}")

        else:
            RuntimeError(f"Unsupported cipher, expected aes, but got {cipher}")   

        content["ct"] = cleartext.decode()

        del content["decrypted"]

def encrypt_and_format_stories(account_key: bytes, *stories: Dict[str, Any]) -> NoReturn:
    for story in stories:
        story["genSettings"]["logitBias"] = dumps(story["genSettings"]["logitBias"])

        for field in ("title", "preview", "content", "description"):
            if field in story:
                if story[field] is None:
                    story[field] = ""
                else:
                    encrypt_content(story[field], account_key)

                    story[field] = dumps(dumps(story[field]))

def build_gen_settings(preset: Preset, banlists: List[BanList], biases: List[BiasGroup]) -> Dict[str, Any]:
    settings = preset.to_settings()

    # TODO: support tokens ?
    settings["badWords"] = [b for banlist in banlists for b in banlist if type(b) is str]
    settings["logitBias"] = { b["value"]: { "bias": b["strength"], "rep_pen_multiplier": b["rep_pen"] }
                                for bias in biases for b in bias if type(b["value"]) is str }

    return settings