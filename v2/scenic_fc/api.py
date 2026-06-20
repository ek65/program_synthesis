from api_utils import API

from scenic_fc.actions import actionAPI
from scenic_fc.constraints import constraintAPI, targetAPI
from scenic_fc.other import *

api = {
    API.domain: 'soccer',
    API.actions: actionAPI,
    API.constraints: constraintAPI,
    API.targetAPI: targetAPI,
    API.color_map: type_to_color,
    API.video_info: video_info,
    API.default_obj: 'coach',
    API.infer_shot: infer_shot,
    API.combine_shot: combine_shot
}