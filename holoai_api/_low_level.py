# Low level interface
# Functions here have no side effect and return the exact response of the request

from aiohttp import ClientSession
from aiohttp.client_reqrep import ClientResponse
from aiohttp.client_exceptions import ClientConnectionError

from re import compile
from json import dumps, loads

from holoai_api.HoloAIError import HoloAIError
from holoai_api.types import Model, Prefix, Order_by, Listing
from holoai_api.Tokenizer import Tokenizer

from typing import Union, Dict, Tuple, List, Any, Optional

#=== INTERNALS ===#
#=== API ===#
class Low_Level:
    _rgx_next_id = compile('"buildId":"([^"]+)"')

    _parent: "HoloAI_API"

    is_schema_validation_enabled: bool

    def __init__(self, parent: "HoloAI_API"):
        self._parent = parent
        self.is_schema_validation_enabled = True

    def _treat_response_object(self, rsp: ClientResponse, content: Any, status: int) -> Any:
        # error is an unexpected fail and usually come with a success status
        if type(content) is dict and "error" in content and content["error"] is not None:    # HoloAI REST API error
            raise HoloAIError(rsp.status, content["error"])

        # success
        if rsp.status == status:
            return content

        if hasattr(rsp, "reason"):                        # HTTPException error
            raise HoloAIError(rsp.status, str(rsp.reason))
        else:
            raise HoloAIError(rsp.status, "Unknown error")

    def _treat_response_bool(self, rsp: ClientResponse, content: Any, status: int) -> bool:
        if rsp.status == status:
            return True

        self._treat_response_object(rsp, content, status)
        return False

    async def _treat_response(self, rsp: ClientResponse, data: Any) -> Any:
        if rsp.content_type == "application/json":
            return (await data.json())
        else:
            return (await data.text())

    def _parse_stream_data(self, stream_content: str) -> Dict[str, Any]:
        stream_data = {}

        for line in stream_content.splitlines():
            colon = line.find(":")
            # TODO: replace by a meaningful error
            assert ":" != -1, f"Malformed data stream line: {line}"

            stream_data[line[:colon]] = line[colon + 1:]

        return stream_data

    async def _treat_response_stream(self, rsp: ClientResponse, data: bytes) -> Any:
        data = data.decode()

        if rsp.content_type == "text/event-stream":
            stream_data = self._parse_stream_data(data)

            # TODO: replace by a meaningful error
            assert "data" in stream_data
            data = loads(stream_data["data"])

        return data

    async def _request(self, method: str, url: str, session: ClientSession,
                             data: Union[Dict[str, Any], str], stream: bool) -> Tuple[ClientResponse, Any]:

        kwargs = {
            "timeout": self._parent._timeout,
            "cookies": self._parent.cookies,
            "headers": self._parent.headers,
        }

        kwargs["json" if type(data) is dict else "data"] = data

        async with session.request(method, url, **kwargs) as rsp:
            if stream:
                async for i in rsp.content.iter_any():
                    yield (rsp, await self._treat_response_stream(rsp, i))
            else:
                yield (rsp, await self._treat_response(rsp, rsp))

    async def request_stream(self, method: str, endpoint: str, data: Optional[Union[Dict[str, Any], str]] = None,
                                   stream: bool = True) -> Tuple[ClientResponse, Any]:
        """
        Send request with support for data streaming

        :param method: Method of the request (get, post, delete)
        :param endpoint: Endpoint of the request
        :param data: Data to pass to the method if needed
        :param stream: Use data streaming for the response
        """

        url = f"{self._parent._BASE_ADDRESS}{endpoint}"

        is_sync = self._parent._session is None
        session = ClientSession() if is_sync else self._parent._session

        try:
            async for i in self._request(method, url, session, data, stream):
                yield i
        except ClientConnectionError as e:      # No internet
            raise HoloAIError(e.errno, str(e))
        # TODO: there may be other request errors to catch
        finally:
            if is_sync:
                await session.close()

    async def request(self, method: str, endpoint: str, data: Optional[Union[Dict[str, Any], str]] = None) -> Tuple[ClientResponse, Any]:
        """
        Send request

        :param method: Method of the request (get, post, delete)
        :param endpoint: Endpoint of the request
        :param data: Data to pass to the method if needed
        """

        async for i in self.request_stream(method, endpoint, data, False):
            return i

    async def _get_next_id(self) -> str:
        rsp, content = await self.request("get", "/404")
        match = self._rgx_next_id.findall(content)

        assert len(match), "Failed to retrieve id. Please generate an issue for this problem"

        return match[0]

    async def request_with_next(self, method: str, endpoint: str, data: Optional[Union[Dict[str, Any], str]] = None) -> Tuple[ClientResponse, Any]:
        """
        Send a request through the "next" framework, refreshing the id if necessary

        :param method: Method of the request (get, post, delete)
        :param endpoint: Endpoint of the request
        :param data: Data to pass to the method if needed
        """

        if not hasattr(self, "_next_id"):
            self._next_id = await self._get_next_id() # get id

        endpoint_with_next = f"/_next/data/{self._next_id}{endpoint}"

        try:
            return await self.request(method, endpoint_with_next, data)
        except HoloAIError as e:
            if e.status != 404:
                raise e

            # failed to retrieve, next_id might be out of date. Refresh id
            self._next_id = await self._get_next_id()
            endpoint_with_next = f"/_next/data/{self._next_id}{endpoint}"

            return await self.request(method, endpoint_with_next, data)

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
        self._treat_response_object(rsp, content, 201)

        return content

    async def get_srp_challenge(self, email: str) -> Dict[str, str]:
        """
        Log in to the account

        :param access_key: Access key of the account

        :return: Response of the request
        """

        assert type(email) is str, f"Expected type 'str' for access_key, but got type '{type(email)}'"

        rsp, content = await self.request("post", "/api/srp_init", { "emailAddress": email })
        self._treat_response_object(rsp, content, 200)

        return content

    async def verify_srp_challenge(self, email: str, A: str, M1: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        rsp, content = await self.request("post", "/api/srp_verify", { "emailAddress": email, "A": A, "M1": M1 })
        self._treat_response_object(rsp, content, 200)

        return (content, rsp.cookies["session"])

    # TODO: delete_user

    # TODO: request_password_change

    # TODO: change_password

    # TODO: get_home (stories and generation settings)
    async def get_home(self) -> Dict[str, Any]:
        rsp, content = await self.request_with_next("get", "/home.json")
        self._treat_response_object(rsp, content, 200)

        return content

    async def get_story(self, story_id: str) -> Dict[str, Any]:
        rsp, content = await self.request_with_next("get", f"/write/{story_id}.json")
        self._treat_response_object(rsp, content, 200)

        return content

    async def create_story(self, desc: str, title: str, prompt: str) -> Dict:
        data = { "description": desc, "story_title": title, "prompt": prompt }

        rsp, content = await self.request("post", "/api/update_story", data)
        self._treat_response_object(rsp, content, 200)

        return content

    async def update_story(self, story_id: str, story: Dict[str, Any]) -> Dict[str, Any]:
        data = { "set_story": { "id": story_id, "story": story } }

        rsp, content = await self.request("post", "/api/update_story", data)
        self._treat_response_object(rsp, content, 200)

        return content

    # TODO: upsert_generation_settings (set story settings)
    async def upsert_generation_settings(self, story_id: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        data = { "set_story": { "id": story_id, "settings": settings } }

        rsp, content = await self.request("post", "/api/upsert_generation_settings", data)
        self._treat_response_object(rsp, content, 200)

        return content

    # TODO: delete_story

    async def read_snapshots(self, story_id: str) -> Dict[str, Any]:
        rsp, content = await self.request("post", "/api/read_snapshots", { "story_id": story_id })
        self._treat_response_object(rsp, content, 200)

        return content

    # TODO: create_folder

    # TODO: delete_folder

    # TODO: move_story

    async def draw_completions(self, prefix: Union[str, List[int]], input: Union[str, List[int]], 
                                     model: Model, module: Optional[str] = None) -> Dict[str, str]:
        """
        :param prefix: Prefix header to be sent to the AI
        :param input: Input to be sent to the AI
        :param model: Model of the AI
        :param module: Id of the module to use

        :return: Generated output
        """

        assert isinstance(prefix, (list, str)), f"Expected type 'list' or 'str' for prefix, but got type '{type(prefix)}'"
        assert isinstance(input, (list, str)), f"Expected type 'list' or 'str' for input, but got type '{type(input)}'"
        assert type(model) is Model, f"Expected type 'Model' for model, but got type '{type(model)}'"
        assert module is None or type(module) is str, f"Expected type 'str' or 'None' for module, but got type '{type(module)}'"

        if type(prefix) is str:
            prefix = Tokenizer.encode(model, prefix)

        if type(input) is str:
            input = Tokenizer.encode(model, input)

        data = {
            "prefixTokens": prefix,
            "promptTokens": input,
            "model_name": model.value,
            "module_id": module,
        }

        rsp, content = await self.request("post", "/api/draw_completions", data)
        self._treat_response_object(rsp, content, 200)

        return content

    async def select_completion(self, completion_id: str, index: int) -> Dict[str, Any]:
        data = { "completion_id": completion_id, "completion_no": index }

        rsp, content = await self.request("post", "/api/select_completion", data)
        self._treat_response_object(rsp, content, 200)

        return content

    async def search_prompt_tunes(self, filter: Dict[str, Any], from_: int = 0, to: int = 10, order: Order_by = Order_by.Creation_date) -> Dict[str, Any]:
        data = { "filter": filter, "from": from_, "to": to, "order_by": order.value }

        rsp, content = await self.request("post", "/api/search_prompt_tunes", data)
        self._treat_response_object(rsp, content, 200)

        return content

    async def read_prompt_tunes(self) -> Dict[str, Any]:
        rsp, content = await self.request("post", "/api/read_prompt_tunes", { })
        self._treat_response_object(rsp, content, 200)

        return content

    async def get_tunes(self) -> Dict[str, Any]:
        rsp, content = await self.request_with_next("get", "/tuner.json")

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
        self._treat_response_object(rsp, content, 200)

        return content

    async def read_prompt_tune_datasets(self):
        # why a post request O_o
        rsp, content = await self.request("post", "/api/read_prompt_tune_datasets", { })
        self._treat_response_object(rsp, content, 200)

        return content

    async def delete_prompt_tune_dataset(self, dataset_id: str):
        data = { "id": dataset_id }

        rsp, content = await self.request("post", "/api/delete_prompt_tune_dataset", data)
        self._treat_response_object(rsp, content, 200)

        return content

    async def create_prompt_tune(self, checkpoints: List[int],
                                       dataset_id: str,
                                       description: str,
                                       destroy_dataset: bool,
                                       listing: Listing,
                                       model: Model,
                                       nsfw: bool,
                                       steps: int,
                                       prefix: Prefix,
                                       tags: List[str],
                                       title: str):



        prefix_value = prefix.value.get("prefix_name")
        prefix_value = {"source": prefix_value} if prefix_value else {}

        data = { "checkpoints": checkpoints,
                 "datasetId": dataset_id,
                 "description": description,
                 "destroyDataAfterTune": destroy_dataset,
                 "listed": listing is not self.Listing.Private,
                 "modelId": model.value,
                 "nsfw": nsfw,
                 "numTrainSteps": steps,
                 "prefix": dumps(prefix_value, separators = (',', ':')),
                 "public": listing is self.Listing.Public,
                 "tags": tags,
                 "title": title
        }

        rsp, content = await self.request("post", "/api/create_prompt_tunes", data)
        self._treat_response_object(rsp, content, 200)

        return content

    async def read_prompt_tune(self, tune_id: str) -> Dict[str, Any]:
        rsp, content = await self.request("post", "/api/read_prompt_tune", { "id": tune_id })
        self._treat_response_object(rsp, content, 200)

        return content

    # TODO: module_delete

    # TODO: module_search