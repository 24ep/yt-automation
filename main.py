import random
from PIL import Image, ImageDraw, ImageFont
import webcolors
import imageio_ffmpeg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import subprocess
import requests
import imageio_ffmpeg
from uuid import uuid4
from supabase import create_client
from dotenv import load_dotenv

# Initialize FastAPI app
app = FastAPI()

# ---------------------------
# Configuration & Environment
# ---------------------------
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BUCKET_NAME = os.getenv("BUCKET_NAME")

class VideoRequest(BaseModel):
    image_url: str
    audio_url: str

class ImageRequest(BaseModel):
    color_name: str
    hex_code: str
    phase: str
    sentence: str

# ---------------------------
# Image Functions (Modified to use provided color)
# ---------------------------
def create_color_image(provided_color_name, hex_code, phase="Beautiful Color", sentence="Randomly Generated"):
    """
    Creates and saves an image using the provided hex code and color name.
    Displays the provided hex and color name on the right-bottom of the image,
    and the labels 'phase' and 'sentence' on the left-bottom.
    
    Parameters:
      provided_color_name: The name of the color (e.g., "red").
      hex_code: The hexadecimal code for the color (e.g., "#FF0000").
      phase: Text label (default: "Beautiful Color").
      sentence: Text label (default: "Randomly Generated").
    """
    img_width, img_height = 1280, 720
    border = 40
    font_path = "C:/Windows/Fonts/arial.ttf"  # Update this path as needed

    # Convert the hex code to RGB
    try:
        color_rgb = webcolors.hex_to_rgb(hex_code)
    except Exception as e:
        raise ValueError(f"Invalid hex code provided: {hex_code}")

    # Create a canvas with a light background
    image = Image.new("RGB", (img_width, img_height), (245, 241, 234))
    draw = ImageDraw.Draw(image)

    # Draw the main color block using the provided color
    draw.rectangle([border, border, img_width - border, img_height - border - 80], fill=color_rgb)

    # Load fonts
    font_small = ImageFont.truetype(font_path, 18)
    font_large = ImageFont.truetype(font_path, 28)

    # Add text:
    # Left-bottom: phase and sentence labels,
    # Right-bottom: hex code and provided color name.
    draw.text((40, img_height - 90), phase, font=font_large, fill="black")
    draw.text((40, img_height - 50), sentence, font=font_small, fill="black")
    draw.text((img_width - 250, img_height - 90), f'{hex_code} - {provided_color_name.title()}', font=font_large, fill="black")

    # Save the generated image locally
    image.save("random_color_image.png")
    # image.show()  # Uncomment this if you want to display the image

# ---------------------------
# Upload Function (supports custom content type)
# ---------------------------
def upload_to_supabase_video(file_path: str, bucket_name: str, object_name: str) -> str:
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



# ---------------------------
# Upload Function (supports custom content type)
# ---------------------------
def upload_to_supabase_image(file_path: str, bucket_name: str, object_name: str, content_type: str = "image/png") -> str:
    """Uploads a file to Supabase storage and returns its public URL."""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    storage = supabase.storage.from_(bucket_name)

    try:
        # Attempt to remove an existing file with the same object name, if it exists
        try:
            storage.remove([object_name])
        except Exception as delete_error:
            print(f"Warning: Could not delete existing file: {delete_error}")

        with open(file_path, "rb") as file:
            storage.upload(object_name, file, {"content-type": content_type})
        return storage.get_public_url(object_name)
    except Exception as e:
        raise RuntimeError(f"Supabase upload failed: {e}")


# ---------------------------
# Video Creation Function (unchanged)
# ---------------------------

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
        video_url = upload_to_supabase_video(output_path, BUCKET_NAME, unique_filename)
        os.remove(output_path)
        return {"video_url": video_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
@app.post("/generate-color-image/")
def generate_color_image_endpoint(data: ImageRequest):

    provided_color_name = data.color_name
    hex_code = data.hex_code
    phase = data.phase
    sentence = data.sentence

    try:
        # Generate the image using the provided color details and labels
        create_color_image(provided_color_name, hex_code, phase, sentence)
        object_name = "random_color_image.png"  # Fixed object name; adjust as needed
        # Upload the image to Supabase with content type "image/png"
        image_url = upload_to_supabase_image("random_color_image.png", "cover", object_name, content_type="image/png")
        os.remove("random_color_image.png")
        return {"image_url": image_url}
    except Exception as e:
        return {"error": e}
