from math import cos, sin
from synth_utils import Demo, Scene, Object, Vector2D

class Translator:

    @classmethod
    def translate(cls, data: dict | list[dict]) -> Demo:

        language = ''
        scene = Scene()
        
        if isinstance(data, list):
            data = [data]

        for d in data:
            _scene, _language = SceneTranslator.translate(d)
            language += _language

        return Demo(scene, language)
    
class ObjectTranslator:

    @classmethod
    def translate(cls, data: dict) -> Object:

        id = data.get('id', '')
        type = data.get('type', '')
        location = [Vector2D.from_dict(v) for v in data.get('position', [])]
        orientation = [Vector2D(cos(a), sin(a)) for a in data.get('orientaiton', [])]

        return Object(
            id=id,
            type=type,
            label=id,
            color='',
            fig='o',
            location=location,
            orientation=orientation
        )

class SceneTranslator:
    
    @classmethod
    def translate(cls, data: dict) -> tuple[Scene, str]:
        data = data.get('scene', data)

        language = data.get('language', '')
        objects = [ObjectTranslator.translate(obj) for obj in data.get('objects', [])]
        dt = data.get('step', 0.0)

        return (Scene(objects, dt), language)