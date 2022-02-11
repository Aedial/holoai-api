from holoai_api.HoloAIError import HoloAIError
from holoai_api._low_level import Low_Level
from holoai_api._high_level import High_Level

from aiohttp import ClientSession, ClientTimeout, ClientTimeout, CookieJar
from multidict import CIMultiDict

from logging import Logger
from typing import NoReturn, Optional

from os.path import dirname, abspath

class HoloAI_API:
    # Constants
    _BASE_ADDRESS: str = "https://writeholo.com"

    # Variables
    _logger: Logger
    _session: Optional[ClientSession]

    _lib_root: str = dirname(abspath(__file__))

    _timeout: ClientTimeout
    _headers: CIMultiDict
    _cookies: CookieJar

    ### Low Level Public API
    low_level: Low_Level
    ### High Level Public API
    high_level: High_Level

    # === Operators === #
    def __init__(self, session: Optional[ClientSession] = None, logger: Optional[Logger] = None):
        # variable passing

        assert session is None or type(session) is ClientSession, f"Expected None or type 'ClientSession' for session, but got type '{type(session)}'"

        # no session = synchronous
        self._session = session

        if logger is None:
            self._logger = Logger("HoloAI_API")
        else:
            self._logger = logger

        self._timeout = ClientTimeout()
        self._headers = CIMultiDict()
        self._cookies = CookieJar()

        # API parts
        self.low_level = Low_Level(self)
        self.high_level = High_Level(self)

    def attach_session(self, session: ClientSession) -> NoReturn:
        """
        Attach a ClientSession, making the requests asynchronous
        """

        assert session is not None
        assert type(session) is ClientSession, f"Expected type 'ClientSession' for session, but got type '{type(session)}'"

        self._session = session

    def detach_session(self) -> NoReturn:
        """
        Detach the current ClientSession, making the requests synchronous
        """

        self._session = None

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

        return self._timeout.total

    @timeout.setter
    def timeout(self, value: int):
        """
        Timeout for a request (in seconds)
        """

        self._timeout = ClientTimeout(value)