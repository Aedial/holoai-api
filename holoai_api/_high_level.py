from json import loads, dumps
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA1

from .utils import format_and_decrypt_stories
from .srp import create_verifier_and_salt, process_challenge

from typing import Dict, Any

class High_Level:
    _parent: "HoloAI_API"

    def __init__(self, parent: "HoloAI_API"):
        self._parent = parent

    async def register(self, email: str, password: str):
        salt, verifier = create_verifier_and_salt(password)

        salt = str(salt)
        verifier = str(verifier)

        key_salt = await self._parent.low_level.register_credentials(email, salt, verifier)

        return key_salt

    async def login(self, email: str, password: str) -> str:
        """
        Log the user in

        :param email: Email of the user
        :param password: Password of the user

        :return: Encryption key
        """
        challenge = await self._parent.low_level.get_srp_challenge(email)

        # verify challenge structure

        s = int(challenge["srp"]["salt"])
        B = int(challenge["srp"]["challenge"])

        password = password.encode()
        x, a, A, k, u, S, M1 = process_challenge(password, s, B)
        A = str(A)
        M1 = str(M1)

        key_salt, cookies = await self._parent.low_level.verify_srp_challenge(email, A, M1)

        # verify key_salt structure

        self._parent._session.cookies = cookies

        key_salt = key_salt["encryptionKeySalt"].encode()
        account_key = PBKDF2(password, key_salt, 16, 1, hmac_hash_module = SHA1)

        # yes, it is what you think it is: a key restricted to the [49:58] | [97:123] domain
        return account_key.hex().encode()

    async def get_user_data(self, account_key: bytes) -> Dict[str, Any]:
        home = await self._parent.low_level.get_home()

        user = home["pageProps"]["user"]
        stories = user["stories"]

        format_and_decrypt_stories(account_key, *stories)

        return user