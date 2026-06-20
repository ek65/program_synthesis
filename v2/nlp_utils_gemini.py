import os
import base64
import cv2
import tiktoken
from PIL import Image
import matplotlib.pyplot as plt
import io
from google.generativeai import GenerativeModel, configure
from google.generativeai.types import content_types
import google.generativeai as genai
import tempfile
import re
import json
import io
import time
import tempfile
import google.generativeai as genai



from apiKey import GEMINI_API_KEY  # Make sure this is defined securely

configure(api_key=GEMINI_API_KEY)

IMGBB_API_KEY = '155765a9436f346d0a9142ebd39efbba'  # Still included for compatibility

def get_im(path):
    with open(path, "rb") as im:
        return im.read()

def get_imi_dir(dir) -> list[str]:
    valid_extensions = {'.png', '.jpg', '.jpeg'}
    files = [f for f in os.listdir(dir) if os.path.splitext(f)[1].lower() in valid_extensions]
    files.sort()
    return [os.path.join(dir, f) for f in files]

class Video:
    def __init__(self, video_path: str, frame_dir: list[str], dt: float = 1.0):
        self.video_path = video_path
        self.frame_dir = frame_dir
        self.sample_rate = dt
        self.dt = dt
        self.duration = len(frame_dir) * dt

    def frame_to_traj_index(self, idx):
        time = idx / self.sample_rate
        return int(time / self.dt)

    def time_to_frame_index(self, t):
        return int(t / self.sample_rate)
    
    def get_frame_bytes(self, frame_index: int) -> bytes:
        if frame_index < 0 or frame_index >= len(self.frame_dir):
            raise IndexError(f"Frame index {frame_index} is out of range.")
        return self.frame_dir[frame_index]


class Chat:
    class Entry:
        def __init__(self, role: str, text: str, im: str = None, file=None):
            self.role = role
            self.text = text
            self.im = im
            self.file = file

    def __init__(self, model: str = 'gemini-2.5-pro'):
        self.model = genai.GenerativeModel(model)

    def __call__(self, input: list[Entry] = [], as_json: bool = False):
        messages = []
        # print("I'm calling gemini")
        uploaded_files = []  # Track files for cleanup
        i = 0
        # print(f"length: {len(input)}")
        # print(f'what are you:{input[52].text}')
        for entry in input:
            parts = []

            # Add text if available
            if entry.text:
                parts.append({"text": entry.text})

            # Handle video file
            if entry.file:
                filename, file_bytes = entry.file

                # Save bytes to temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
                    temp_file.write(file_bytes)
                    temp_path = temp_file.name

                # Upload to Gemini
                uploaded_file = genai.upload_file(
                    path=temp_path,
                    mime_type="video/mp4",
                    display_name=filename
                )

                # Wait until file is in ACTIVE state
                while True:
                    file_status = genai.get_file(uploaded_file.name)
                    if file_status.state.name == "ACTIVE":
                        break
                    time.sleep(1)

                parts.append(uploaded_file)
                uploaded_files.append(uploaded_file.name)
                
            
            # messages.append({
            #     "role": entry.role,
            #     "parts": parts
            # })
            role = entry.role.lower()
            if role not in ("user", "model"):
                role = "user"  # fallback to user if invalid

            messages.append({
                "role": role,
                "parts": parts
            })
            # print(f"loop {i} done")
            # i +=1

        # Call Gemini
        # print("Call is happening rn gemini")
        response = self.model.generate_content(messages)
        # print("Gemini gave answer")
        # Optional: clean up uploaded files
        for file_id in uploaded_files:
            try:
                genai.delete_file(file_id)
            except Exception:
                pass  # Ignore if deletion fails

        if as_json:
            match = re.search(r"```json\s*([\s\S]*?)\s*```", response.text)
            if match:
                json_block = match.group(1).strip()
                try:
                    return json.loads(json_block)
                except json.JSONDecodeError as e:
                    print("Gemini returned invalid JSON:")
                    print(json_block)
                    raise e
            else:
                raise ValueError(f"No valid ```json block found in Gemini response:\n{response.text}")
        else:
            return response.text