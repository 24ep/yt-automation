import os
import random
import subprocess
import requests
from uuid import uuid4
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
import webcolors
import imageio_ffmpeg
from supabase import create_client

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

# ---------------------------
# Configuration & Environment
# ---------------------------
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BUCKET_NAME = os.getenv("BUCKET_NAME")

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
    draw.text((img_width - 270, img_height - 90), f'{hex_code} - {provided_color_name.title()}', font=font_large, fill="black")

    # Save the generated image locally
    image.save("random_color_image.png")
    # image.show()  # Uncomment this if you want to display the image

# ---------------------------
# Upload Function (supports custom content type)
# ---------------------------
def upload_to_supabase(file_path: str, bucket_name: str, object_name: str, content_type: str = "video/mp4") -> str:
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
    """Downloads an image and an audio file, merges them into a video using ffmpeg, and returns the video file path."""
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

# ---------------------------
# Flask App Setup
# ---------------------------
# app = Flask(__name__)

# @app.route('/generate-video/', methods=['POST'])
@app.post("/generate-video/")
def generate_video_endpoint():
    """
    Expects JSON with:
      - image_url: URL to the image
      - audio_url: URL to the audio
    Returns a JSON containing the public video URL after creating the video and uploading it to Supabase.
    """
    data = request.get_json()
    if not data or 'image_url' not in data or 'audio_url' not in data:
        return jsonify({"error": "Please provide image_url and audio_url in the JSON body."}), 400

    try:
        unique_filename = "output_video.mp4"
        output_path = create_video(data['image_url'], data['audio_url'], unique_filename)
        video_url = upload_to_supabase(output_path, BUCKET_NAME, unique_filename)
        os.remove(output_path)
        return jsonify({"video_url": video_url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# @app.route('/generate-color-image/', methods=['POST'])
@app.post("/generate-color-image/")
def generate_color_image_endpoint():
    """
    Expects JSON with the following keys:
      - color_name: The name of the color (e.g., "red").
      - hex_code: The hexadecimal code for the color (e.g., "#FF0000").
      - phase: (Optional) Label text (default: "Beautiful Color").
      - sentence: (Optional) Label text (default: "Randomly Generated").
    Generates an image using the provided color, uploads it to Supabase, and returns its public URL.
    """
    data = request.get_json() or {}
    if 'color_name' not in data or 'hex_code' not in data:
        return jsonify({"error": "Please provide both 'color_name' and 'hex_code' in the JSON body."}), 400

    provided_color_name = data['color_name']
    hex_code = data['hex_code']
    phase = data.get('phase', "Beautiful Color")
    sentence = data.get('sentence', "Randomly Generated")

    try:
        # Generate the image using the provided color details and labels
        create_color_image(provided_color_name, hex_code, phase, sentence)
        object_name = "random_color_image.png"  # Fixed object name; adjust as needed
        # Upload the image to Supabase with content type "image/png"
        image_url = upload_to_supabase("random_color_image.png", "cover", object_name, content_type="image/png")
        os.remove("random_color_image.png")
        return jsonify({"image_url": image_url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# # ---------------------------
# # Run the Flask App
# # ---------------------------
# if __name__ == "__main__":
#     app.run(debug=True)
