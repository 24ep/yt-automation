import random
from PIL import Image, ImageDraw, ImageFont , ImageOps , ImageFilter  
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
import json
import base64
import mimetypes
from google import genai
from google.genai import types

# Initialize FastAPI app
app = FastAPI()

# ---------------------------
# Configuration & Environment
# ---------------------------
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BUCKET_NAME = os.getenv("BUCKET_NAME")
GIMINI_API_KEY = os.getenv("GIMINI_API_KEY")
class VideoRequest(BaseModel):
    image_url: str
    audio_url: str

class ImageRequest(BaseModel):
    color_name: str
    hex_code: str
    phase: str
    sentence: str

class ImageGiminiRequest(BaseModel):
    promtp: str

class BorderSizeRequest(BaseModel):
    border_size: str
    image_url: str
    phase: str
    sentence: str
    flower: str



def convert_png_to_jpeg(png_path, jpeg_path):
    with Image.open(png_path) as img:
        rgb_img = img.convert("RGB")  # JPEG doesn't support alpha channel
        rgb_img.save(jpeg_path, "JPEG")

def save_binary_file(file_name, data):
    f = open(file_name, "wb")
    f.write(data)
    f.close()

        
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
    border = 50
    
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
    draw.text((img_width - 230, img_height - 90), f'{hex_code} - {provided_color_name.title()}', font=font_large, fill="black")
    
    # Save the generated image locally
    image.save("random_color_image.jpeg")
    # image.show()  # Uncomment to display the image

def get_audio_duration(audio_path):
    command = [
        'ffprobe', 
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'json',
        audio_path
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    data = json.loads(result.stdout)
    return float(data['format']['duration'])
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

    audio_duration = get_audio_duration(audio_path)

    subprocess.run([
        ffmpeg_path,
        '-y',
        '-loop', '1',              # Loop the input image
        '-i', image_path,
        '-c:v', 'libx264',
        '-t', str(audio_duration),
        '-r', '30',                # Frame rate (adjust if needed)
        '-pix_fmt', 'yuv420p',
        'temp_video.mp4'
    ], check=True)

        # Merge the temporary video with the audio
    subprocess.run([
        ffmpeg_path,
        '-y',
        '-i', 'temp_video.mp4',
        '-i', audio_path,
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-shortest',               # Stop output when the shorter stream (likely audio) ends
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

@app.post("/generate-gimini-image/")
def generate(data:ImageGiminiRequest):
    promtp = data.promtp
    client = genai.Client(
        api_key=GIMINI_API_KEY,
    )

    model = "gemini-2.0-flash-exp-image-generation"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=f"""{str(promtp)}"""),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        response_modalities=[
            "image",
            "text",
        ],
        response_mime_type="text/plain",
    )

    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        if not chunk.candidates or not chunk.candidates[0].content or not chunk.candidates[0].content.parts:
            continue
        if chunk.candidates[0].content.parts[0].inline_data:
            file_name = "export.png"
            inline_data = chunk.candidates[0].content.parts[0].inline_data
            file_extension = mimetypes.guess_extension(inline_data.mime_type)
            save_binary_file(file_name, inline_data.data)

            # Convert PNG → JPEG
            convert_png_to_jpeg(file_name, "export.jpeg")

            object_name = "export.jpeg"  # Fixed object name; adjust as needed
            # Upload the image to Supabase with content type "image/jpg"
            image_url = upload_to_supabase_image("export.jpeg", "cover", object_name, content_type="image/jpeg")
            os.remove("export.jpeg")
            return {"image_url": image_url}
       
        else:
            print(chunk.text)


@app.post("/add-image-border/")
def add_border_and_text_from_url(data:BorderSizeRequest):
    border_size = int(data.border_size)
    image_url = data.image_url
    phase = data.phase
    sentence = data.sentence
    flower = data.flower
    output_filename = "export_border_image.jpeg"
    """
    Downloads an image from a URL, adds a border and text, uploads to Supabase, and returns the public URL.
    """
    # Download image from URL
    response = requests.get(image_url)
 

    image = Image.open(BytesIO(response.content)).convert("RGB")

   # Resize image to 1280x720 with high-quality resampling
    target_size = (1280, 720)
    image = image.resize(target_size, Image.Resampling.LANCZOS)

    # Border and text parameters
    border_color = (239, 235, 224)
    quote_text = phase
    quote_author = sentence
    title_text = phase
    subtitle_text = sentence
    font_path = "times.ttf"  # Ensure this font exists or change to a bundled font
    extra_bottom_space = 150

    # Add border
    bordered_img = ImageOps.expand(image, border=border_size, fill=border_color)

    # New canvas
    new_width = bordered_img.width
    new_height = bordered_img.height + extra_bottom_space
    final_img = Image.new("RGB", (new_width, new_height), border_color)
    final_img.paste(bordered_img, (0, 0))

    # Draw text
    draw = ImageDraw.Draw(final_img)
    try:
        title_font = ImageFont.truetype(font_path, size=34)
        subtitle_font = ImageFont.truetype(font_path, size=22)
        quote_font = ImageFont.truetype(font_path, size=18)
    except IOError:
        title_font = subtitle_font = quote_font = ImageFont.load_default()

    quote_text_full = f"{quote_text}\n{quote_author}"
    quote_x =  new_width - 250
    quote_y = bordered_img.height + 15
    draw.text((quote_x, quote_y), flower, font=quote_font, fill=(30, 30, 30))
    
    title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
    subtitle_bbox = draw.textbbox((0, 0), subtitle_text, font=subtitle_font)
    
    title_w = title_bbox[2] - title_bbox[0]
    title_h = title_bbox[3] - title_bbox[1]
    subtitle_w = subtitle_bbox[2] - subtitle_bbox[0]
    subtitle_h = subtitle_bbox[3] - subtitle_bbox[1]
    
    right_margin = 40
    title_x = title_w - right_margin
    subtitle_x = subtitle_w - right_margin
    title_y = bordered_img.height + 15
    subtitle_y = title_y + title_h + 10
    
    draw.text((title_x, title_y), title_text, font=title_font, fill=(30, 30, 30))
    draw.text((subtitle_x, subtitle_y), subtitle_text, font=subtitle_font, fill=(30, 30, 30))

    # Save to a temporary file
    temp_path = output_filename
    final_img.save(temp_path)
    image_url = upload_to_supabase_image(output_filename, "cover", output_filename, content_type="image/jpeg")
    # Clean up
    os.remove(temp_path)

    return {"image_url": public_url}

    
