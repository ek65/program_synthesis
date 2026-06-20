from api_utils import API

from factory_api.actions import actionAPI
from factory_api.constraints import constraintAPI
# from factory_api.other import *

api = {
    API.domain: 'factory working',
    API.actions: actionAPI,
    API.constraints: constraintAPI,
    # API.color_map: type_to_color,
    # API.video_info: video_info
}