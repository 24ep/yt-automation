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
from io import BytesIO

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
    
    This version downloads a Google Font at runtime without storing it to disk.
    
    Parameters:
      provided_color_name: The name of the color (e.g., "red").
      hex_code: The hexadecimal code for the color (e.g., "#FF0000").
      phase: Text label (default: "Beautiful Color").
      sentence: Text label (default: "Randomly Generated").
    """
    img_width, img_height = 1280, 720
    border = 40
    
    # Convert the hex code to RGB
    try:
        color_rgb = webcolors.hex_to_rgb(hex_code)
    except Exception:
        raise ValueError(f"Invalid hex code provided: {hex_code}")
    
    # Create a canvas with a light background
    image = Image.new("RGB", (img_width, img_height), (250, 249, 246))
    draw = ImageDraw.Draw(image)
    
    # Draw the main color block using the provided color
    draw.rectangle([border, border, img_width - border, img_height - border - 80], fill=color_rgb)
    
    font_path = "times.ttf"  # Update this path as needed
    
    # Load the font directly from memory
    # Load fonts
    font_small = ImageFont.truetype(font_path,18)
    font_large = ImageFont.truetype(font_path,28)

    
    
    # Add text labels
    draw.text((40, img_height - 90), phase, font=font_large, fill="black")
    draw.text((40, img_height - 50), sentence, font=font_small, fill="black")
    draw.text((img_width - 250, img_height - 90), f'{hex_code} - {provided_color_name.title()}', font=font_large, fill="black")
    
    # Save the generated image locally
    image.save("random_color_image.jpeg")
    # image.show()  # Uncomment to display the image

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
def upload_to_supabase_image(file_path: str, bucket_name: str, object_name: str, content_type: str = "image/jpeg") -> str:
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
        '-loop', '1',                   # Loop the image indefinitely
        '-framerate', '30',             # Explicit frame rate for the static image
        '-i', image_path,               # Input image file (1280x720)
        '-i', audio_path,               # Input audio file
        '-c:v', 'libx264',              # Video codec
        '-preset', 'fast',              # Optional: adjust as needed for speed/quality
        '-tune', 'stillimage',          # Optimize encoding for a still image
        '-c:a', 'aac',                  # Audio codec
        '-b:a', '192k',                 # Audio bitrate
        '-pix_fmt', 'yuv420p',          # Ensure broad compatibility
        '-shortest',                   # End the output when the shortest input ends
        '-y',                          # Overwrite output file if it exists
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

    
    # Generate the image using the provided color details and labels
    create_color_image(provided_color_name, hex_code, phase, sentence)
    object_name = "random_color_image.jpeg"  # Fixed object name; adjust as needed
    # Upload the image to Supabase with content type "image/jpg"
    image_url = upload_to_supabase_image("random_color_image.jpeg", "cover", object_name, content_type="image/jpeg")
    os.remove("random_color_image.jpeg")
    return {"image_url": image_url}
    
