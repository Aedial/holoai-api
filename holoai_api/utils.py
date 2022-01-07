from base64 import b64encode, b64decode
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA256
from functools import partial
from json import dumps, loads

from typing import Dict, Union, List, Tuple, Any, Optional, NoReturn

dumps = partial(dumps, separators = (',', ':'))

def decrypt_story_content(content: Dict[str, Any], key: bytes, password: bytes) -> NoReturn:
    ct = b64decode(content["ct"])

    # CBC, CFB, OFB, OPENPGP
    iv = b64decode(content.get("iv", ""))

    salt = b64decode(content["salt"])

    cipher = content.get("cipher", "")
    mode = content.get("mode", "")
    if cipher == "aes":
        if mode == "ccm":
            key = PBKDF2(password, salt, 16, 10000, hmac_hash_module = SHA256)
            nonce = key[:8]
            aes = AES.new(key, AES.MODE_CCM, nonce = nonce)
        else:
            RuntimeError(f"Unsupported mode for AES, expected CCM, but got {mode}")

        print(aes.decrypt(ct[:-8]))
#        print(aes.decrypt_and_verify(ct[:-8], ct[-8:]))

    else:
        RuntimeError(f"Unsupported cipher, expected aes, but got {cipher}")   

    content["decrypted"] = True

def format_and_decrypt_stories(key: bytes, password: bytes, *stories: Dict[str, Any]):
    for story in stories:
        story["genSettings"]["logitBias"] = loads(story["genSettings"]["logitBias"])

        story["content"] = loads(story["content"])
        if type(story["content"]) is str:	# safer than checking story["encrypted"]
            story["content"] = loads(story["content"])

            decrypt_story_content(story["content"], key, password)