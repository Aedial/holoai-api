from holoai_api.HoloAIError import HoloAIError
from holoai_api.FakeClientSession import FakeClientSession

from aiohttp import ClientSession, ClientError
from aiohttp.client_reqrep import ClientResponse
from aiohttp.client import _RequestContextManager
from aiohttp.http_exceptions import HttpProcessingError

from requests import request as sync_request, Response
from enum import Enum

from typing import Union, Dict, Tuple, List, Iterable, Any, NoReturn, Optional

class SyncResponse():
	_rsp: Response

	def __init__(self, rsp: Response):
		self._rsp = rsp
		self.status = rsp.status_code
		self.reason = rsp.reason
		self.content_type = rsp.headers["Content-Type"].split(';')[0]

	async def text(self):
		return self._rsp.text

	async def json(self):
		return self._rsp.json()

#=== INTERNALS ===#
#=== API ===#
class Low_Level:
	_parent: "HoloAI_API"
	_session: Union[ClientSession, FakeClientSession]
	_is_async: bool

	def __init__(self, parent: "HoloAI_API"):
		self._is_async = parent._is_async

		assert not self._is_async or isinstance(parent._session, ClientSession), "Session must be of class ClientSession for asynchronous operations"
		assert self._is_async or isinstance(parent._session, FakeClientSession), "Session must be of class FakeClientSession for synchronous operations"

		self._parent = parent
		self._session = parent._session

	def _treat_response_object(self, rsp: Union[ClientResponse, SyncResponse], content: Any, status: int) -> Any:
		# success
		if rsp.status == status:
			return content

		# not success, but valid response
		if type(content) is dict and "error" in content:	# HoloAI REST API error
			raise HoloAIError(rsp.status, content["error"])
		elif hasattr(rsp, "reason"):						# HTTPException error
			raise HoloAIError(rsp.status, str(rsp.reason))
		else:
			raise HoloAIError(rsp.status, "Unknown error")

	def _treat_response_bool(self, rsp: Union[ClientResponse, SyncResponse], content: Any, status: int) -> bool:
		if rsp.status == status:
			return True

		treat_response_object(rsp, content, status)
		return False

	async def _treat_response(self, rsp: Union[ClientResponse, SyncResponse]) -> Any:
		if rsp.content_type == "application/json":
			return (await rsp.json())
		else:
			return (await rsp.text())

	async def _request_async(self, method: str, url: str, data: Optional[Union[Dict[str, Any], str]] = None) -> Tuple[ClientResponse, Any]:
		"""
		:param url: Url of the request
		:param method: Method of the request from ClientSession
		:param data: Data to pass to the method if needed
		"""	
		if type(data) is dict:	# data transforms dict in str
			async with self._session.request(method, url, json = data) as rsp:
				return (rsp, await self._treat_response(rsp))
		else:
			async with self._session.request(method, url, data = data) as rsp:
				return (rsp, await self._treat_response(rsp))

	async def _request_sync(self, method: str, url: str, data: Optional[Union[Dict[str, Any], str]] = None) -> Tuple[ClientResponse, Any]:
		"""
		:param url: Url of the request
		:param method: Method of the request from the request library
		:param data: Data to pass to the method if needed
		"""

		timeout = self._session.timeout.total
		headers = self._parent._session.headers

		if type(data) is dict:
			with sync_request(method, url, headers = headers, json = data) as rsp:
				rsp = SyncResponse(rsp)
				return (rsp, await self._treat_response(rsp))
		else:
			with sync_request(method, url, headers = headers, data = data) as rsp:
				rsp = SyncResponse(rsp)
				return (rsp, await self._treat_response(rsp))

	async def request(self, method: str, endpoint: str, data: Optional[Union[Dict[str, Any], str]] = None) -> Tuple[ClientResponse, Any]:
		"""
		:param endpoint: Endpoint of the request
		:param request_method: Method of the reqest from ClientSession
		:param data: Data to pass to the method if needed
		"""

		url = f"{self._parent._BASE_ADDRESS}{endpoint}"

		if self._is_async:
			return await self._request_async(method, url, data)
		else:
			return await self._request_sync(method, url, data)

	async def is_reachable(self) -> bool:
		"""
		Check if the HoloAI API is reachable

		:return: True if reachable, False if not
		"""
		rsp, content = await self.request("get", "/api")
		return self._treat_response_bool(rsp, content, 200)

	async def register_credentials(self, email: str, salt: str, verifier: str):
		"""
		Register a new account

		:param email: Email of the player
		:param salt: Salt given by srp
		:param verifier: Verifier given by srp
		"""

		assert type(email) is str, f"Expected type 'str' for email, but got type '{type(email)}'"
		assert type(salt) is str, f"Expected type 'str' for salt, but got type '{type(salt)}'"
		assert type(verifier) in (str, None), f"Expected type 'str' for verifier, but got type '{type(verifier)}'"

		rsp, content = await self.request("post", "/register_credentials", { "emailAddress": email, "salt": salt, "verifier": verifier })
		rsp = self._treat_response_object(rsp, content, 201)

		# FIXME: handle cases where the response is corrupted

		return rsp

	async def get_srp_challenge(self, email: str) -> Dict[str, str]:
		"""
		Log in to the account

		:param access_key: Access key of the account

		:return: Response of the request
		"""

		assert type(email) is str, f"Expected type 'str' for access_key, but got type '{type(email)}'"

		rsp, content = await self.request("post", "/srp_init", { "emailAddress": email })
		return self._treat_response_object(rsp, content, 200)

	async def verify_srp_challenge(self, email: str, A: str, M1: str):
		rsp, content = await self.request("post", "/srp_verify", { "emailAddress": email, "A": A, "M1": M1 })

		return self._treat_response_object(rsp, content, 200), rsp.cookies.get("session")

	# TODO: delete_user

	# TODO: request_password_change

	# TODO: change_password

	# TODO: get_home (stories and generation settings)

	# TODO: create_story

	# TODO: update_story

	# TODO: upsert_generation_settings (set story settings)

	# TODO: delete_story

	# TODO: create_folder

	# TODO: delete_folder

	# TODO: move_story

	# FIXME: get proper names
	class ModelName(Enum):
		Model = "model-2-7"

	async def draw_completions(self, input: List[int], model: ModelName, module: Optional[str] = None) -> Dict[str, str]:
		"""
		:param input: Input to be sent the AI
		:param model: Model of the AI
		:param module: Id of the module to use

		:return: Generated output
		"""

		assert type(input) is list, f"Expected type 'list' for input, but got type '{type(input)}'"
		assert type(model) is self.ModelName, f"Expected type 'ModelName' for model, but got type '{type(model)}'"
		assert type(module) is str or module is None, f"Expected type 'str' or 'None' for module, but got type '{type(module)}'"

		# FIXME
		prefix = [ 4895, 10459, 2404, 17201, 313, 3970, 2430, 24886, 1298, 15, 553, 22872, 2404, 37, 316, 680, 2430, 13664, 1298, 20, 2388, 92 ]
		args = {
			"model_name": model.value,
			"module_id": module,
			"prefixTokens": prefix,
			"promptTokens": input,
		}

		rsp, content = await self.request("post", "/draw_completions", args)
		return self._treat_response_object(rsp, content, 200)

	# TODO: update_story

	# TODO: module_train

	# TODO: module_delete

	# TODO: module_search