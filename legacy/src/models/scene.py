from api.football import Coach, Target
from api.objects.player import Player
from object import Object
from annotations.annotation import Annotation
import numpy as np
import re

class Scene:
    def __init__(self, objects=[], duration=0.0, timestep=0.0, language='', annotations=[]):

        self.duration = duration
        self.timestep = timestep

        self.objects = objects
        self.allObjects = objects

        self.duration = duration
        self.timestep = timestep

        self.language = language
        self.annotations = annotations
        self.demos = [self]

    def set_time(self, t):
        for obj in self.objects:
            obj.set_time(t, self.timestep)

    def add(self, objects):
        if isinstance(objects, list):
            self.objects += objects
        else:
            self.objects += [objects]

    def add_demo(self, scene: 'Scene'):
        self.demos += [scene]

    @classmethod
    def from_dict(cls, data, objectsAPI):

        data = data.get('scene', data)

        lang = ""
        if data.get('language') != "" and data.get('language') != None:
            lang = data['language']
        scene = cls(language=lang)
        scene.objects = [Object.from_dict(objData, objectsAPI) for objData in data.get('objects', [])]
        scene.annotations = [Annotation.from_dict(antnData) for antnData in data.get('annotations', [])]
        scene.language = Scene.replace_annotations(scene.language, scene.annotations)

        if len(scene.objects):
            scene.timestep = data.get('step', 0.0)
            scene.duration = len(scene.objects[0]._position) * scene.timestep
        else:
            raise Exception(f"Imported scene has no objects.")
        
        # adding target here as last position of coach for now
        # TODO: change this when we get target object/annotation?
        t = Target('target')
        for o in scene.objects:
            if isinstance(o, Coach):
                t.at(o._position[-1])
        scene.objects.append(t)

        # necessary objects
        necessaryObjects = []

        for o in scene.objects:
            if isinstance(o, Player) or isinstance(o, Target):
                # print(o, o.type)
                necessaryObjects.append(o)

        scene.allObjects = scene.objects
        scene.objects = necessaryObjects

        return scene
    
    @classmethod
    def replace_annotations(cls, input_string, annotations):
        # Create a dictionary for quick lookup of annotation text by id
        annotation_dict = {annotation.id: str(annotation) for annotation in annotations}

        # Define the replacement function
        def replacer(match):
            # Extract the id from the match
            annotation_id = match.group(1)  # Match group is now a string to align with dict keys
            # Replace with the corresponding annotation text if it exists
            return annotation_dict.get(annotation_id, match.group(0))

        # Use regex to find patterns like [0], [4], etc., and replace them
        result = re.sub(r'\[(\d+)\]', replacer, input_string)

        return result
    
    def extend(self, scene):

        if self.objects:
            assert [obj.id for obj in self.objects] == [obj.id for obj in scene.objects], "Failed to extend Scene: Objects in the scene do not match."
            assert self.timestep == scene.timestep, "Failed to extend Scene: Timesteps do not match."

        self.timestep = scene.timestep

        if self.language:
            self.language += f'\n\n{scene.language}'
        else:
            self.language = scene.language

        if self.objects:
            for obj_a, obj_b in zip(self.objects, scene.objects):
                obj_a.extend(obj_b)
        else:
            self.objects = scene.objects

        self.duration = len(self.objects[0]._position) * self.timestep