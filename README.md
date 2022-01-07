# holoai-api
Python API for the HoloAI REST API

The module is intended to be used by developers as a help for using HoloAI's REST API.


### Examples:
The examples are in the example folder. Each example is working and can be used as a test.
Each example can be called with `python <name>.py`.



### Module:
The actual module is in the holoai-api folder. Valid imports are : `holoai_api.HoloAI_API`, `holoai_api.HoloAIError`, and everything under the `holoai_api.utils` namespace.
This module is asynchronous, and, as such, must be run with asyncio. An example can be found in any file of the example directory.