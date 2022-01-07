import srp

srp.rfc5054_enable()
srp.no_username_in_x()

from .srp import create_verifier_and_salt, process_challenge

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

	async def login(self, email: str, password: str):
		challenge = await self._parent.low_level.get_srp_challenge(email)

		# verify challenge structureemail

		s = int(challenge["srp"]["salt"])
		B = int(challenge["srp"]["challenge"])

		x, a, A, k, u, S, M1 = process_challenge(password, s, B)
		A = str(A)
		M1 = str(M1)

		key_salt, cookies = await self._parent.low_level.verify_srp_challenge(email, A, M1)

		# verify key_salt structure

		self._parent._session.cookies = cookies

		return key_salt