from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import subprocess
import requests
import imageio_ffmpeg
from uuid import uuid4
from supabase import create_client
from dotenv import load_dotenv
import os

# Initialize FastAPI app
app = FastAPI()



# Load environment variables from .env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BUCKET_NAME = os.getenv("BUCKET_NAME")

# Define the request body schema
class VideoRequest(BaseModel):
    image_url: str
    audio_url: str

def upload_to_supabase(file_path: str, bucket_name: str, object_name: str) -> str:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    storage = supabase.storage.from_(bucket_name)

    try:
        try:
            storage.remove([object_name])
        except Exception as delete_error:
            print(f"Warning: Could not delete existing file: {delete_error}")

        with open(file_path, "rb") as file:
            # Specify the content type as video/mp4
            storage.upload(object_name, file, {
                "content-type": "video/mp4"
            })

        return storage.get_public_url(object_name)
    except Exception as e:
        raise RuntimeError(f"Supabase upload failed: {e}")


def create_video(image_url: str, audio_url: str, output_filename: str) -> str:
    image_path = 'temp_image.jpg'
    audio_path = 'temp_audio.mp3'
    output_path = output_filename

    with open(image_path, 'wb') as f:
        f.write(requests.get(image_url).content)

    with open(audio_path, 'wb') as f:
        f.write(requests.get(audio_url).content)

    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

    subprocess.run([
        ffmpeg_path,
        '-loop', '1',
        '-i', image_path,
        '-i', audio_path,
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-shortest',
        '-pix_fmt', 'yuv420p',
        '-y',
        output_path
    ], check=True)

    os.remove(image_path)
    os.remove(audio_path)

    return output_path

@app.post("/generate-video/")
def generate_video(data: VideoRequest):
    try:
        unique_filename = "output_video.mp4"
        output_path = create_video(data.image_url, data.audio_url, "output_video.mp4")
        video_url = upload_to_supabase(output_path, BUCKET_NAME, unique_filename)
        os.remove(output_path)
        return {"video_url": video_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
