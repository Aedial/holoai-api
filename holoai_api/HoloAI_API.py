from holoai_api.HoloAIError import HoloAIError
from holoai_api.FakeClientSession import FakeClientSession
from holoai_api._low_level import Low_Level
from holoai_api._high_level import High_Level

from aiohttp import ClientSession, ClientTimeout, ClientTimeout
from multidict import CIMultiDict

from logging import Logger, NullHandler
from typing import Union, Dict, Tuple, List, Iterable, Any, NoReturn, Optional, MethodDescriptorType

from os.path import dirname, abspath

class HoloAI_API:
	# Constants
	_BASE_ADDRESS: str = "https://writeholo.com"

	# Variables
	_token: Optional[str] = None
	_logger: Logger
	_session: ClientSession
	_is_async: bool

	_lib_root: str = dirname(abspath(__file__))

	### Low Level Public API
	low_level: Low_Level
	### High Level Public API
	high_level: High_Level

	# === Operators === #
	def __init__(self, session: Optional[ClientSession] = None, logger: Optional[Logger] = None):
		# variable passing

		# no session = synchronous
		self._is_async = (session is not None)
		if self._is_async:
			self._session = session
		else:
			self._session = FakeClientSession()

		if logger is None:
			self._logger = Logger("HoloAI_API")
			self._logger.addHandler(NullHandler())
		else:
			self._logger = logger

		# API parts
		self.low_level = Low_Level(self)
		self.high_level = High_Level(self)

	@property
	def headers(self) -> CIMultiDict:
		"""
		Headers of the HTTP requests
		"""

		return self._session.headers

	@property
	def timeout(self):
		"""
		Timeout for a request (in seconds)
		"""

		if self._session.timeout is None or self._session.timeout.total is None:
			return 300	# aiohttp's default

		return self._session.timeout.total

	@timeout.setter
	def timeout(self, value: int):
		"""
		Timeout for a request (in seconds)
		"""

		self._session.timeout = ClientTimeout(value)