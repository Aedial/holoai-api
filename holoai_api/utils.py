from base64 import b64encode, b64decode
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA256
from functools import partial
from json import dumps, loads

from typing import Dict, Union, List, Tuple, Any, Optional, NoReturn

dumps = partial(dumps, separators = (',', ':'))
def clamp(l, v, h):
    return (l if v < l else h if h < v else v)

# kudos to Schmitty#5079 for coming up with the way to convert iv to nonce (extracted from ccm.js in sjcl)
def decrypt_sjcl_ccm(content: Dict[str, Any], account_key) -> bytes:
    salt = b64decode(content["salt"])
    key_len = content["ks"] // 8
    key_iter = content["iter"]
    key = PBKDF2(account_key, salt, key_len, key_iter, hmac_hash_module = SHA256)

    iv = b64decode(content["iv"])
    tag_len = content["ts"] // 8
    ciphertext = b64decode(content["ct"])
    cipher_len = len(ciphertext) - tag_len

    # nonce = iv[0:13] down to iv[0:11] depending on ciphertext length
    nonce_size = 13 - clamp(0, (cipher_len.bit_length() // 8) - 2, 2)

    # limit slice size if iv is not big enough
    nonce_size = min(nonce_size, len(iv))

    nonce = iv[:nonce_size]
    ciphertext = ciphertext[:cipher_len]
    tag = ciphertext[cipher_len:]

    aes = AES.new(key, AES.MODE_CCM, nonce = nonce)
    cleartext = aes.decrypt(ciphertext)

    # FIXME: verify why tag does't work (might be another of these damned nonstandard functions)
#    cleartext = aes.decrypt_and_verify(ciphertext, tag)

    return cleartext

# FIXME: get proper errors ?
def decrypt_story_content(content: Dict[str, Any], account_key: bytes, loads_ct: Optional[bool] = False) -> NoReturn:
    cipher = content.get("cipher")
    mode = content.get("mode")
    if cipher == "aes":
        if mode == "ccm":
            cleartext = decrypt_sjcl_ccm(content, account_key)
        else:
            RuntimeError(f"Unsupported mode for AES, expected CCM, but got {mode}")

    else:
        RuntimeError(f"Unsupported cipher, expected aes, but got {cipher}")   

    content["ct"] = cleartext.decode()
    if loads_ct:
        content["ct"] = loads(content["ct"])

    content["decrypted"] = True

def format_and_decrypt_stories(account_key: bytes, *stories: Dict[str, Any]):
    for story in stories:
        story["genSettings"]["logitBias"] = loads(story["genSettings"]["logitBias"])

        for field in ("title", "preview", "content", "description"):
            if story.get(field):
                story[field] = loads(story[field])

                if type(story[field]) is str:	# safer than checking story["encrypted"]
                    story[field] = loads(story[field])

                decrypt_story_content(story[field], account_key, (field == "content"))