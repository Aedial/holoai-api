# Low level interface
# Functions here have no side effect and return the exact response of the request

from holoai_api.HoloAIError import HoloAIError
from holoai_api.FakeClientSession import FakeClientSession

from aiohttp import ClientSession, ClientError
from aiohttp.client_reqrep import ClientResponse
from aiohttp.client import _RequestContextManager
from aiohttp.http_exceptions import HttpProcessingError

from requests import request as sync_request, Response
from enum import Enum, auto

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
    NEXT_PATH = "/_next/data/mD2hyP2lid1GjolKPXBZ5"

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
        if type(content) is dict and "error" in content:    # HoloAI REST API error
            raise HoloAIError(rsp.status, content["error"])
        elif hasattr(rsp, "reason"):                        # HTTPException error
            raise HoloAIError(rsp.status, str(rsp.reason))
        else:
            raise HoloAIError(rsp.status, "Unknown error")

    def _treat_response_bool(self, rsp: Union[ClientResponse, SyncResponse], content: Any, status: int) -> bool:
        if rsp.status == status:
            return True

        self._treat_response_object(rsp, content, status)
        return False

    async def _treat_response(self, rsp: Union[ClientResponse, SyncResponse]) -> Any:
        if rsp.content_type == "application/json":
            return (await rsp.json())
        else:
            return (await rsp.text())

    async def _request_async(self, method: str, url: str, data: Optional[Union[Dict[str, Any], str]] = None) -> Tuple[Union[ClientResponse, SyncResponse], Any]:
        """
        :param url: Url of the request
        :param method: Method of the request from ClientSession
        :param data: Data to pass to the method if needed
        """    
        if type(data) is dict:    # data transforms dict in str
            async with self._session.request(method, url, json = data) as rsp:
                return (rsp, await self._treat_response(rsp))
        else:
            async with self._session.request(method, url, data = data) as rsp:
                return (rsp, await self._treat_response(rsp))

    async def _request_sync(self, method: str, url: str, data: Optional[Union[Dict[str, Any], str]] = None) -> Tuple[Union[ClientResponse, SyncResponse], Any]:
        """
        :param url: Url of the request
        :param method: Method of the request from the request library
        :param data: Data to pass to the method if needed
        """

        timeout = self._session.timeout.total
        headers = self._parent._session.headers
        cookies = self._parent._session.cookies

        if type(data) is dict:
            with sync_request(method, url, headers = headers, cookies = cookies, json = data) as rsp:
                rsp = SyncResponse(rsp)
                return (rsp, await self._treat_response(rsp))
        else:
            with sync_request(method, url, headers = headers, cookies = cookies, data = data) as rsp:
                rsp = SyncResponse(rsp)
                return (rsp, await self._treat_response(rsp))

    async def request(self, method: str, endpoint: str, data: Optional[Union[Dict[str, Any], str]] = None) -> Tuple[Union[ClientResponse, SyncResponse], Any]:
        """
        Send request

        :param method: Method of the request (get, post, delete)
        :param endpoint: Endpoint of the request
        :param data: Data to pass to the method if needed
        """

        url = f"{self._parent._BASE_ADDRESS}{endpoint}"

        if self._is_async:
            return await self._request_async(method, url, data)
        else:
            return await self._request_sync(method, url, data)

    async def _get_next_id(self):
        # FIXME
        raise NotImplementedError()

    async def request_with_next(self, endpoint: str, data: Optional[Union[Dict[str, Any], str]]) -> Tuple[Union[ClientResponse, SyncResponse], Any]:
        """
        Send a request through the "next" framework, refreshing the id if necessary

        :param method: Method of the request (get, post, delete)
        :param endpoint: Endpoint of the request
        :param data: Data to pass to the method if needed
        """

        if not hasattr(self, "_next_id"):
            self._next_id = self._get_next_id() # get id

        endpoint = f"/_next/data/{self._next_id}/{endpoint}"

        try:
            return self.request(method, endpoint, data)
        except HoloAIError as e:
            if e.status != 404:
                raise e

            # failed to retrieve, next_id might be stub. Refresh id
            self._next_id = self._get_next_id()
            return self.request(method, endpoint, data)

    async def is_reachable(self) -> bool:
        """
        Check if the HoloAI API is reachable

        :return: True if reachable, False if not
        """

        # FIXME: doesn't seem to work. Doesn't exist ?

        rsp, content = await self.request("get", "/")
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

        rsp, content = await self.request("post", "/api/register_credentials", { "emailAddress": email, "salt": salt, "verifier": verifier })
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

        rsp, content = await self.request("post", "/api/srp_init", { "emailAddress": email })
        return self._treat_response_object(rsp, content, 200)

    async def verify_srp_challenge(self, email: str, A: str, M1: str):
        rsp, content = await self.request("post", "/api/srp_verify", { "emailAddress": email, "A": A, "M1": M1 })

        return self._treat_response_object(rsp, content, 200), rsp.cookies.get("session")

    # TODO: delete_user

    # TODO: request_password_change

    # TODO: change_password

    # TODO: get_home (stories and generation settings)
    async def get_home(self) -> Dict[str, Any]:
        rsp, content = await self.request("get", f"{self.NEXT_PATH}/home.json")

        return self._treat_response_object(rsp, content, 200)

    async def get_story(self, story_id: str) -> Dict[str, Any]:
        rsp, content = await self.request("get", f"{self.NEXT_PATH}/write/{story_id}.json")

        return self._treat_response_object(rsp, content, 200)

    # TODO: create_story
    async def update_story(self, desc: str, title: str, prompt: str) -> Dict:
        data = { "description": desc, "story_title": title, "prompt": content }
        rsp, content = await self.request("post", "/api/update_story", data)

        return self._treat_response_object(rsp, content, 200)

    # TODO: update_story
    async def update_story(story_id: str, story: Dict[str, Any]) -> Dict[str, Any]:
        data = { "set_story": { "id": story_id, "settings": settings } }
        rsp, content = await self.request("post", "/api/update_story", data)

        return self._treat_response_object(rsp, content, 200)

    # TODO: upsert_generation_settings (set story settings)
    async def upsert_generation_settings(story_id: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        data = { "set_story": { "id": story_id, "settings": settings } }
        rsp, content = await self.request("post", "/api/upsert_generation_settings", data)

        return self._treat_response_object(rsp, content, 200)

    # TODO: delete_story

    async def read_snapshots(self, story_id: str) -> Dict[str, Any]:
        data = { "story_id": story_id }
        rsp, content = await self.request("post", "/api/read_snapshots", data)

        return self._treat_response_object(rsp, content, 200)

    # TODO: create_folder

    # TODO: delete_folder

    # TODO: move_story

    # FIXME: get proper names
    class ModelName(Enum):
        Model = "model-2-7"

    class Prefix(Enum):
        Novel = { "prefix_name": "{source: googreads}", "tokens": [ 4895, 10459, 2404, 11274, 40779, 2430, 24886, 1298, 15, 92 ] }
        Fanfic = { "prefix_name": "{source: ao3}", "tokens": [4895, 10459, 2404, 5488, 18, 2430, 24886, 1298, 15, 92 ] }
        Romance = { "prefix_name": "{source: literotica}", "tokens": [ 4895, 10459, 2404, 17201, 313, 3970, 2430, 24886, 1298, 15, 553, 22872, 2404, 37, 316, 680, 20662 ] }
        CYOA = { "prefix_name": "{source: cyoa}" }
        Generic = { "prefix_name": "{}", "tokens": [ 4895, 24886, 1298, 15, 92 ] }

    async def draw_completions(self, input: List[int], model: ModelName, prefix: Prefix, module: Optional[str] = None) -> Dict[str, str]:
        """
        :param input: Input to be sent the AI
        :param model: Model of the AI
        :param module: Id of the module to use

        :return: Generated output
        """

        assert type(input) is list, f"Expected type 'list' for input, but got type '{type(input)}'"
        assert type(model) is self.ModelName, f"Expected type 'ModelName' for model, but got type '{type(model)}'"
        assert type(prefix) is self.Prefix, f"Expected type 'Prefix' for prefix, but got type '{type(prefix)}'"
        assert module is None or type(module) is str, f"Expected type 'str' or 'None' for module, but got type '{type(module)}'"

        args = {
            "model_name": model.value,
            "module_id": module,
            "prefixTokens": prefix.value["tokens"],
            "promptTokens": input,
        }

        rsp, content = await self.request("post", "/api/draw_completions", args)
        return self._treat_response_object(rsp, content, 200)

    async def select_completion(self, completion_id: str, index: int) -> Dict[str, Any]:
        data = { "completion_id": completion_id, "completion_no": index }
        rsp, content = await self.request("post", "/api/select_completion", data)

        return self._treat_response_object(rsp, content, 200)

    class ORDER_BY(Enum):
        CREATION_DATE = "creation_date"

    async def search_prompt_tunes(self, filter: Dict[str, Any], from_: int = 0, to: int = 10, order: ORDER_BY = ORDER_BY.CREATION_DATE) -> Dict[str, Any]:
        data = { "filter": filter, "from": from_, "to": to, "order_by": order.value }
        rsp, content = await self.request("post", "/api/search_prompt_tunes", data)

        return self._treat_response_object(rsp, content, 200)

    async def read_prompt_tunes(self) -> Dict[str, Any]:
        rsp, content = await self.request("post", "/api/read_prompt_tunes", { })

        return self._treat_response_object(rsp, content, 200)

    async def get_tunes(self) -> Dict[str, Any]:
        rsp, content = await self.request("get", f"{self.NEXT_PATH}/tuner.json")

        return self._treat_response_object(rsp, content, 200)

    async def create_prompt_tune_dataset(self, name: str, documents: List[Dict[str, str]]) -> Dict[str, Any]:
        assert type(name) is str, f"Expected type 'str' for name, but got type '{type(name)}'"
        assert type(documents) is list, f"Expected type 'str' for documents, but got type '{type(documents)}'"

        for i, document in enumerate(documents):
            assert "filename" in document, f"Expected key 'filename' in document #{i}"
            assert "text" in document, f"Expected key 'text' in document #{i}"

            assert type(document["filename"]) is str, f"Expected type 'str' for 'filename' in document #{i}, but got type '{type(document['filename'])}'"
            assert type(document["text"]) is str, f"Expected type 'str' for 'text' in document #{i}, but got type '{type(document['text'])}'"

        data = { "name": name, "documents": documents }
        rsp, content = await self.request("post", "/api/create_prompt_tune_dataset", data)

        return self._treat_response_object(rsp, content, 200)

    async def read_prompt_tune_datasets(self):
        # why a post request O_o
        rsp, content = await self.request("post", "/api/read_prompt_tune_datasets", { })

        return self._treat_response_object(rsp, content, 200)

    async def delete_prompt_tune_dataset(self, dataset_id: str):
        data = { "id": dataset_id }
        rsp, content = await self.request("post", "/api/delete_prompt_tune_dataset", data)

        return self._treat_response_object(rsp, content, 200)

    class Listing(Enum):
        Private = auto()
        Unlisted = auto()
        Public = auto()


    async def create_prompt_tune(self, checkpoints: List[int],
                                       dataset_id: str,
                                       description: str,
                                       destroy_dataset: bool,
                                       listing: Listing,
                                       model: ModelName,
                                       nsfw: bool,
                                       steps: int,
                                       prefix: Prefix,
                                       tags: List[str],
                                       title: str):



        data = { "checkpoints": checkpoints,
                 "datasetId": dataset_id,
                 "description": description,
                 "destroyDataAfterTune": destroy_dataset,
                 "listed": listing is not self.Listing.Private,
                 "modelId": model.value,
                 "nsfw": nsfw,
                 "numTrainSteps": steps,
                 "prefix": prefix.value["prefix_name"],
                 "public": listing is self.Listing.Public,
                 "tags": tags,
                 "title": title
        }

        rsp, content = await self.request("post", "/api/create_prompt_tunes", data)

        return self._treat_response_object(rsp, content, 200)

    async def read_prompt_tune(self, tune_id: str) -> Dict[str, Any]:
        rsp, content = await self.request("post", "/api/read_prompt_tune", { "id": tune_id })

        return self._treat_response_object(rsp, content, 200)

    # TODO: module_delete

    # TODO: module_search