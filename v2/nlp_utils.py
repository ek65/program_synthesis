
import os
import base64
from openai import OpenAI
import cv2
import tiktoken
from PIL import Image
import matplotlib.pyplot as plt
import io
from apiKey import OPENAI_API_KEY

IMGBB_API_KEY = '155765a9436f346d0a9142ebd39efbba'
# OPENAI_API_KEY = 'YOUR_OPENAI_KEY'

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
        self.frame_dir = frame_dir  # Use frame_dir consistently
        self.sample_rate = dt
        self.dt = dt
        self.duration = len(frame_dir) * dt

    def frame_to_traj_index(self, idx):
        # converts frame index to trajectory index where trajectory is collected at every dt seconds
        time = idx / self.sample_rate
        return int(time / self.dt)

    def time_to_frame_index(self, t):
        # converts time in seconds to frame index <-- where the rate at which frame is sampled at every sample_rate seconds
        return int(t / self.sample_rate)

    def __getitem__(self, key: float) -> Image.Image:
        """
        Return the keyframe image corresponding to the given time (in seconds) of the video.
        """
        # print(f"Video duration: {self.duration} seconds")
        # print(f"Key: {key} seconds")
        # print(f"Number of frames: {len(self.frame_dir)}")
        # print(f"Frame directory: {self.frame_dir}")
        # print(f"Frame interval: {self.dt} seconds")
        # print(f"Video path: {self.video_path}")
        if not (0 <= key <= self.duration):
            if key > 0:
                frame_file = self.frame_dir[-1]
            else:
                frame_file = self.frame_dir[0]
        else:
            idx = int(key / self.sample_rate)
            frame_file = self.frame_dir[min(idx, len(self.frame_dir) - 1)]
        return Image.open(frame_file)
    
    def get_frame_bytes(self, key: float) -> bytes:
        """
        Retrieve the keyframe (using __getitem__) and return its bytes (JPEG format).
        """
        img = self[key]  # Get the PIL image via __getitem__
        with io.BytesIO() as output:
            img.save(output, format="JPEG")
            return output.getvalue()
    
    def show(self, key: float):
        plt.imshow(self[key])
        plt.axis('off')
        plt.show()
    
    @classmethod
    def from_dir(cls, video_path: str, dt=1.0, k=1.0) -> 'Video':
        output_dir = os.path.join(os.path.dirname(video_path), 'frames')
        frame_dir, _ = vid_to_frames(video_path, output_dir, dt, k)
        return cls(video_path, frame_dir, dt)

def vid_to_frames(video_path, output_dir=None, samplerate=1/2, k=1.0):
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")
        
    if output_dir is None:
        video_dir = os.path.dirname(video_path)
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        output_dir = os.path.join(video_dir, f"{video_name}_frames")
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Check if frames already exist (from previous auto_synthesis run)
    existing_frames = [f for f in os.listdir(output_dir) if f.startswith('frame_') and f.endswith('.jpg')]
    if existing_frames:
        print(f"Found {len(existing_frames)} existing frames in {output_dir}")
        print("Skipping frame extraction since frames already exist from previous processing")
        # Return existing frame paths sorted by frame number
        existing_frames.sort()
        frame_paths = [os.path.join(output_dir, f) for f in existing_frames]
        
        # Calculate approximate total tokens for existing frames
        # This is an estimate since we're not re-encoding
        encoding = tiktoken.get_encoding("cl100k_base")
        estimated_tokens = len(existing_frames) * 765  # Use average token count per frame
        
        return frame_paths, estimated_tokens
    
    # If no existing frames found, proceed with frame extraction
    print(f"No existing frames found. Extracting frames from video...")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Error opening video file: {video_path}")
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    print(f"FPS: {fps}")
    print(f"Samplerate: {samplerate}")
    frame_interval = int(fps * samplerate)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"Total # of frames: {total_frames}")
    print(f"Duration of Video: {total_frames / fps} seconds")
    
    original_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    original_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    new_width = int(original_width * k)
    new_height = int(original_height * k)
    
    frame_paths = []
    frame_count = 0
    acc_frame = 0
    total_tokens = 0
    
    encoding = tiktoken.get_encoding("cl100k_base")  # GPT-4 encoding
    
    while acc_frame < total_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, acc_frame)
        ret, frame = cap.read()
        
        if not ret:
            break
            
        if k != 1.0:
            frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
        
        frame_path = os.path.join(output_dir, f"frame_{frame_count:04d}.jpg")
        cv2.imwrite(frame_path, frame)  # Save each frame to disk 
        frame_paths.append(frame_path)
        
        _, buffer = cv2.imencode('.jpg', frame)
        base64_string = base64.b64encode(buffer).decode('utf-8')
        frame_tokens = len(encoding.encode(base64_string))
        total_tokens += frame_tokens
        
        frame_count += 1
        acc_frame += frame_interval
    print(f"Total # of frames saved: {frame_count}")
    cap.release()
    return frame_paths, total_tokens

client = OpenAI(api_key=OPENAI_API_KEY)

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

class Chat:

    class Entry:
        def __init__(self, role: str, text: str, imgs_paths: list = None, im = None, im_url = None):
            self.role = role
            self.text = text
            self.img_frames = None
            
            if imgs_paths:
                base64Frames = []
                for im_path in imgs_paths:
                    base64_image = encode_image(im_path)
                    base64Frames.append(base64_image)
                    self.img_frames = base64Frames
            elif im_url:
                self.im_url = im_url
            elif im:
                # Encode the image bytes directly as base64 and create a data URI.
                base64_string = base64.b64encode(im).decode('utf-8')
                self.im_url = f"data:image/jpeg;base64,{base64_string}"
            else:
                self.im_url = ''

        def to_dict(self) -> dict:
            content = []
            
            if self.text:
                content.append({
                    'type': 'text',
                    'text': self.text
                })

            if self.img_frames:
                content.extend(["This is a video as a sequence of image frames.", *map(lambda x: {"image": x}, self.img_frames)])

                # Add proper OpenAI image format for each frame
                for frame_base64 in self.img_frames:
                    content.append({
                        'type': 'image_url',
                        'image_url': {
                            'url': f"data:image/jpeg;base64,{frame_base64}"
                        }
                    })

            if hasattr(self, 'im_url') and self.im_url:
                content.append({
                    'type': 'image_url',
                    'image_url': {
                        'url': self.im_url
                    }
                })

            obj = {
                'role': self.role,
                'content': content
            }
            return obj


    def __init__(self, client, model='gpt-5-mini'):
        self.model = model
        self.client = client
        self.last_usage = None  # Store usage from last API call

    def __call__(self, input: list[Entry] = [], json: bool = False):
        chat = self.client.chat.completions.create(
            model=self.model,
            messages=[entry.to_dict() for entry in input],
            response_format={'type': 'json_object' if json else 'text'}
        )
        
        # Store usage information for token tracking
        self.last_usage = chat.usage
        
        return chat.choices[0].message.content
    
    def get_last_token_usage(self):
        """
        Returns token usage from the last API call.
        Returns dict with prompt_tokens, completion_tokens, total_tokens
        """
        if self.last_usage:
            return {
                'prompt_tokens': self.last_usage.prompt_tokens,
                'completion_tokens': self.last_usage.completion_tokens,
                'total_tokens': self.last_usage.total_tokens
            }
        return None