import json
from math import cos, sin
from synth_utils_gemini import Demo, Scene, Object, Vector2D
from nlp_utils import Video
from tqdm import tqdm
import os

class UnityTranslator:

    @classmethod
    # def translate(cls, id: str, data: dict, vid_dir: str | None = None, sample_rate: float = 1.0, scale_factor: float = 1.0) -> Demo:
    #     scene, language = SceneTranslator.translate(data)
    #     pause_times = SceneTranslator.extract_pause_times(data)
    #     video = Video.from_dir(vid_dir, dt=sample_rate, k=scale_factor)
    #     demo = Demo(id, scene, language, video)
    #     demo.pause_times = pause_times
    #     return demo
    def translate(cls, id: str, data: dict, vid_dir: str | None = None, sample_rate: float = 1.0, scale_factor: float = 1.0) -> Demo:
        scene, language = SceneTranslator.translate(data)
        pause_times = SceneTranslator.extract_pause_times(data)

        with open(vid_dir, 'rb') as f:
            video_bytes = f.read()  # video is now a `bytes` object
        video = Video.from_dir(vid_dir, dt=sample_rate, k=scale_factor)

        demo = Demo(id, scene, language, video, video_bytes)
        demo.pause_times = pause_times
        print('Demo objects')
        demos = [demo]
        print({f"(Type: {obj.type}) (ID: {obj.id}) (label: {obj.label})" for demo in demos for obj in demo.scene.objects})
        return demo
        
    @classmethod
    def get_from(cls, dir: list[str] | str, sample_rate: float = 1.0, scale_factor: float = 1.0) -> list[Demo] | Demo:
        demo_dirs = [os.path.join(dir, item) for item in os.listdir(dir)
                    if os.path.isdir(os.path.join(dir, item)) and "demonstration" in item.lower()]
        demo_dirs.sort()
        result = []

        for idx, subdir in enumerate(tqdm(demo_dirs, desc="Importing")):
            # Get first JSON file
            json_dir = os.path.join(subdir, 'json_segments')
            json_files = [f for f in os.listdir(json_dir) if f.endswith('.json')]
            if not json_files:
                continue  # or raise an error
            data_path = os.path.join(json_dir, sorted(json_files)[0])
            with open(data_path, 'r') as file:
                data = json.load(file)

            # Get first video file
            video_dir = os.path.join(subdir, 'videos')
            video_exts = ('.mp4', '.mov', '.avi', '.mkv', '.webm')
            video_files = [f for f in os.listdir(video_dir) if f.lower().endswith(video_exts)]
            if not video_files:
                continue  # or raise an error
            vid_path = os.path.join(video_dir, sorted(video_files)[0])

            id = f'demo_{idx}' if len(demo_dirs) > 1 else ''
            result.append(cls.translate(id, data, vid_dir=vid_path, sample_rate=sample_rate, scale_factor=scale_factor))

        return result if len(result) > 1 else result[0]


class SceneTranslator:
    def __init__(self):
        pass

    @classmethod
    def ground_language(cls, data: dict) -> str:
        language = data.get('language', None)
        annotations = data.get('annotations', None)
        assert annotations is not None

        # Replace any clicking caption enclosed by parentheses
        language = language.replace("(ball clicks)", " ")
        result = []
        depth = 0
        for char in language:
            if char == '(':
                depth += 1
            elif char == ')':
                if depth > 0:
                    depth -= 1
            else:
                if depth == 0:
                    result.append(char)
        language = ''.join(result)

        for item in annotations:
            id = item['id']
            ty = item['type']

            if ty == "ReceiveBall":
                language = language.replace(f"[{id}]", f"[{item['player']} receives or gets possession of the ball]")
            elif ty == 'Pass':
                language = language.replace(f"[{id}]", f"[{item['from']} passes to {item['to']}]")
            elif ty == 'Through Pass':
                x = item['to']['x']
                y = item['to']['y']
                position = (x,y)
                language = language.replace(f"[{id}]", f"[{item['from']} passes to {str(position)}]")
            elif ty == 'Shoot Goal':
                language = language.replace(f"[{id}]", f"[Took shoot ball action.]")
            elif ty == 'PauseAction':
                language = language.replace(f"[{id}]", f"[Pause in the demonstration]")
            elif ty == 'Raise Hand':
                language = language.replace(f"[{id}]", f"[{item['player']} raises hand.]")
            elif ty == 'Pick Up':
                language = language.replace(f"[{id}]", f"[{item['player']} picks up {item['object']}.]")
            elif ty == 'Put Down':
                language = language.replace(f"[{id}]", f"[{item['player']} puts down {item['object']}.]")
            elif ty == 'Received Item':
                language = language.replace(f"[{id}]", f"[{item['player']} recieved {item['object']}.]")
            elif ty == 'Reference':
                language = language.replace(f"[{id}]", f"[{item['obj']} was referenced.]")
            elif ty == 'Point':
                language = language.replace(f"[{id}]", f"[Coach points at {item['point']}.]")
            elif ty == 'TriggerPass':
                language = language.replace(f"[{id}]", f"[Coach calls for {item['from']} to pass the ball.]")
            elif ty == 'Intercept':
                language = language.replace(f"[{id}]", f"[{item['from']} intercepts the ball by forcibly gaining possession.]")
            elif ty == 'node annotation':
                language = language.replace(f"[{id}]", f"[User annotated node {item['stateId']} with description {item['description']}.]")
            elif ty == 'edge annotation':
                language = language.replace(f"[{id}]", f"[User annotated edge {item['transitionId']} with description {item['description']}.]")
            else:
                raise NotImplementedError(f"This ANNOTATION type ({ty}) is not handled yet")
            
        return language

    @classmethod
    def translate(cls, data: dict) -> tuple[Scene, str]:
        data = data.get('scene', data) # we assume that scene is formatted in Unity
        language = cls.ground_language(data)
        objects = [ObjectTranslator.translate(obj) for obj in data.get('objects', [])]
        # print('Are here any objects?')
        # print(objects)
        dt = data.get('step', None)

        return (Scene(objects, dt), language)
    
    @classmethod
    def extract_pause_times(cls, data: dict) -> list[float]:
        """Extract times when the user paused the demonstration"""
        data = data.get('scene', data)
        pause_times = []
        annotations = data.get('annotations', [])
        click_times = data.get('clickTimes', {})
        
        for annotation in annotations:
            id = annotation['id']
            ty = annotation['type']
            if id in click_times and ty == 'PauseAction':
                pause_times.append(float(click_times[id]))
        
        # Sort pause times in ascending order
        pause_times.sort()
        return pause_times
    
class ObjectTranslator:

    @classmethod
    def translate(cls, data: dict) -> Object:

        id = data.get('id', '')
        type = data.get('type', '')
        location = [Vector2D.from_dict(v) for v in data.get('position', [])]
        # orientation = [Vector2D(cos(a), sin(a)) for a in data.get('orientation', [])]

        return Object(
            id=id,
            type=type,
            label=id,
            color='',
            fig='o',
            location=location,
            # orientation=orientation
        )