from base64 import b64encode, b64decode
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA256
from functools import partial
from json import dumps, loads

from typing import Dict, Union, List, Tuple, Any, Optional, NoReturn

dumps = partial(dumps, separators = (',', ':'))

# kudos for Schmitty#5079 for coming up with this function (extracted from ccm.js in sjcl)
def get_sjcl_ccm_encryption_info_from_iv(content: Dict[str, Any]) -> bytes:
    iv = b64decode(content["iv"])
    tag_len = content["ts"] // 8
    ct = b64decode(content["ct"])

    iv_len = len(iv)
    ct_len = len(ct) - tag_len

    # L = max(ct_len.get_bytes(), 4)
    L = 2
    while (L < 4) and (ct_len >> 8 * L):
        L += 1

    if L < 15 - iv_len:
        L = 15 - ivl

    return iv[:(15 - L)], ct[:-tag_len], ct[-tag_len:]

def decrypt_story_content(content: Dict[str, Any], account_key: bytes) -> NoReturn:
    salt = b64decode(content["salt"])

    cipher = content.get("cipher", "")
    mode = content.get("mode", "")
    if cipher == "aes":
        if mode == "ccm":
            key_len = content["ks"] // 8
            key_iter = content["iter"]

            account_key = account_key.hex().encode()
            key = PBKDF2(account_key, salt, key_len, key_iter, hmac_hash_module = SHA256)

            nonce, ct, tag = get_sjcl_ccm_encryption_info_from_iv(content)
            aes = AES.new(key, AES.MODE_CCM, nonce = nonce)
            content["ct"] = loads(aes.decrypt(ct).decode())
        else:
            RuntimeError(f"Unsupported mode for AES, expected CCM, but got {mode}")

    else:
        RuntimeError(f"Unsupported cipher, expected aes, but got {cipher}")   

    content["decrypted"] = True

def format_and_decrypt_stories(account_key: bytes, *stories: Dict[str, Any]):
    for story in stories:
        story["genSettings"]["logitBias"] = loads(story["genSettings"]["logitBias"])

        story["content"] = loads(story["content"])
        if type(story["content"]) is str:	# safer than checking story["encrypted"]
            story["content"] = loads(story["content"])

            decrypt_story_content(story["content"], account_key)