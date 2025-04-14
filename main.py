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
from flask import Flask, request, jsonify

# ---------------------------
# Configuration & Environment
# ---------------------------
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BUCKET_NAME = os.getenv("BUCKET_NAME")

# ---------------------------
# Random Color & Image Functions
# ---------------------------
css3_colors = {
    'aliceblue': '#F0F8FF', 'antiquewhite': '#FAEBD7', 'aqua': '#00FFFF', 'aquamarine': '#7FFFD4',
    'azure': '#F0FFFF', 'beige': '#F5F5DC', 'bisque': '#FFE4C4', 'black': '#000000',
    'blanchedalmond': '#FFEBCD', 'blue': '#0000FF', 'blueviolet': '#8A2BE2', 'brown': '#A52A2A',
    'burlywood': '#DEB887', 'cadetblue': '#5F9EA0', 'chartreuse': '#7FFF00', 'chocolate': '#D2691E',
    'coral': '#FF7F50', 'cornflowerblue': '#6495ED', 'cornsilk': '#FFF8DC', 'crimson': '#DC143C',
    'cyan': '#00FFFF', 'darkblue': '#00008B', 'darkcyan': '#008B8B', 'darkgoldenrod': '#B8860B',
    'darkgray': '#A9A9A9', 'darkgreen': '#006400', 'darkkhaki': '#BDB76B', 'darkmagenta': '#8B008B',
    'darkolivegreen': '#556B2F', 'darkorange': '#FF8C00', 'darkorchid': '#9932CC', 'darkred': '#8B0000',
    'darksalmon': '#E9967A', 'darkseagreen': '#8FBC8F', 'darkslateblue': '#483D8B', 'darkslategray': '#2F4F4F',
    'darkturquoise': '#00CED1', 'darkviolet': '#9400D3', 'deeppink': '#FF1493', 'deepskyblue': '#00BFFF',
    'dimgray': '#696969', 'dodgerblue': '#1E90FF', 'firebrick': '#B22222', 'floralwhite': '#FFFAF0',
    'forestgreen': '#228B22', 'fuchsia': '#FF00FF', 'gainsboro': '#DCDCDC', 'ghostwhite': '#F8F8FF',
    'gold': '#FFD700', 'goldenrod': '#DAA520', 'gray': '#808080', 'green': '#008000',
    'greenyellow': '#ADFF2F', 'honeydew': '#F0FFF0', 'hotpink': '#FF69B4', 'indianred': '#CD5C5C',
    'indigo': '#4B0082', 'ivory': '#FFFFF0', 'khaki': '#F0E68C', 'lavender': '#E6E6FA',
    'lavenderblush': '#FFF0F5', 'lawngreen': '#7CFC00', 'lemonchiffon': '#FFFACD', 'lightblue': '#ADD8E6',
    'lightcoral': '#F08080', 'lightcyan': '#E0FFFF', 'lightgoldenrodyellow': '#FAFAD2', 'lightgray': '#D3D3D3',
    'lightgreen': '#90EE90', 'lightpink': '#FFB6C1', 'lightsalmon': '#FFA07A', 'lightseagreen': '#20B2AA',
    'lightskyblue': '#87CEFA', 'lightslategray': '#778899', 'lightsteelblue': '#B0C4DE', 'lightyellow': '#FFFFE0',
    'lime': '#00FF00', 'limegreen': '#32CD32', 'linen': '#FAF0E6', 'magenta': '#FF00FF',
    'maroon': '#800000', 'mediumaquamarine': '#66CDAA', 'mediumblue': '#0000CD', 'mediumorchid': '#BA55D3',
    'mediumpurple': '#9370DB', 'mediumseagreen': '#3CB371', 'mediumslateblue': '#7B68EE', 'mediumspringgreen': '#00FA9A',
    'mediumturquoise': '#48D1CC', 'mediumvioletred': '#C71585', 'midnightblue': '#191970', 'mintcream': '#F5FFFA',
    'mistyrose': '#FFE4E1', 'moccasin': '#FFE4B5', 'navajowhite': '#FFDEAD', 'navy': '#000080',
    'oldlace': '#FDF5E6', 'olive': '#808000', 'olivedrab': '#6B8E23', 'orange': '#FFA500',
    'orangered': '#FF4500', 'orchid': '#DA70D6', 'palegoldenrod': '#EEE8AA', 'palegreen': '#98FB98',
    'paleturquoise': '#AFEEEE', 'palevioletred': '#DB7093', 'papayawhip': '#FFEFD5', 'peachpuff': '#FFDAB9',
    'peru': '#CD853F', 'pink': '#FFC0CB', 'plum': '#DDA0DD', 'powderblue': '#B0E0E6',
    'purple': '#800080', 'rebeccapurple': '#663399', 'red': '#FF0000', 'rosybrown': '#BC8F8F',
    'royalblue': '#4169E1', 'saddlebrown': '#8B4513', 'salmon': '#FA8072', 'sandybrown': '#F4A460',
    'seagreen': '#2E8B57', 'seashell': '#FFF5EE', 'sienna': '#A0522D', 'silver': '#C0C0C0',
    'skyblue': '#87CEEB', 'slateblue': '#6A5ACD', 'slategray': '#708090', 'snow': '#FFFAFA',
    'springgreen': '#00FF7F', 'steelblue': '#4682B4', 'tan': '#D2B48C', 'teal': '#008080',
    'thistle': '#D8BFD8', 'tomato': '#FF6347', 'turquoise': '#40E0D0', 'violet': '#EE82EE',
    'wheat': '#F5DEB3', 'white': '#FFFFFF', 'whitesmoke': '#F5F5F5', 'yellow': '#FFFF00',
    'yellowgreen': '#9ACD32'
}

def get_closest_color_name(hex_code):
    """Finds the closest CSS3 color name to the given hex code."""
    r, g, b = webcolors.hex_to_rgb(hex_code)
    min_dist = float('inf')
    closest_name = None
    for name, hex_val in css3_colors.items():
        r2, g2, b2 = webcolors.hex_to_rgb(hex_val)
        dist = (r - r2) ** 2 + (g - g2) ** 2 + (b - b2) ** 2
        if dist < min_dist:
            min_dist = dist
            closest_name = name
    return closest_name

def random_color():
    """Generates a random color in RGB and hex format."""
    r, g, b = [random.randint(0, 255) for _ in range(3)]
    hex_code = '#{:02X}{:02X}{:02X}'.format(r, g, b)
    return (r, g, b), hex_code

def create_color_image(beautiful_color_text="Beautiful Color", randomly_generated_text="Randomly Generated"):
    """
    Creates and saves an image of a randomly generated color.
    The texts are added as labels to the image.
    """
    img_width, img_height = 1280, 720
    border = 40
    font_path = "C:/Windows/Fonts/arial.ttf"  # Update if needed

    color_rgb, hex_code = random_color()
    color_name = get_closest_color_name(hex_code)

    # Create canvas with a light background
    image = Image.new("RGB", (img_width, img_height), (245, 241, 234))
    draw = ImageDraw.Draw(image)

    # Draw main color block
    draw.rectangle([border, border, img_width - border, img_height - border - 80], fill=color_rgb)

    # Load fonts
    font_small = ImageFont.truetype(font_path, 18)
    font_large = ImageFont.truetype(font_path, 28)

    # Add text elements:
    # Left-bottom: custom labels,
    # Right-bottom: hex code and color name.
    draw.text((40, img_height - 90), beautiful_color_text, font=font_large, fill="black")
    draw.text((40, img_height - 50), randomly_generated_text, font=font_small, fill="black")
    draw.text((img_width - 270, img_height - 90), f'{hex_code} - {color_name.title()}', font=font_large, fill="black")

    # Save the generated image
    image.save("random_color_image.png")
    # Optionally, remove image.show() if not needed in a web environment.
    # image.show()

# ---------------------------
# Upload Function (supports custom content type)
# ---------------------------
def upload_to_supabase(file_path: str, bucket_name: str, object_name: str, content_type: str = "video/mp4") -> str:
    """Uploads a file to Supabase storage and returns its public URL."""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    storage = supabase.storage.from_(bucket_name)

    try:
        # Attempt to delete an existing file with the same object name if it exists
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
app = Flask(__name__)

@app.route('/generate-video/', methods=['POST'])
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

@app.route('/generate-color-image/', methods=['POST'])
def generate_color_image_endpoint():
    """
    Expects JSON with optional keys:
      - beautiful_color: Text for a label (default: "Beautiful Color")
      - randomly_generated: Text for a label (default: "Randomly Generated")
    Generates a random color image, uploads it to Supabase, and returns its public URL.
    """
    data = request.get_json() or {}
    beautiful_color_text = data.get('beautiful_color', "Beautiful Color")
    randomly_generated_text = data.get('randomly_generated', "Randomly Generated")

    try:
        # Generate the image locally
        create_color_image(beautiful_color_text, randomly_generated_text)
        # Create a unique object name for the image; here we're using a fixed name
        object_name = "random_color_image.png"
        # Upload the image to Supabase with content type "image/png"
        image_url = upload_to_supabase("random_color_image.png", BUCKET_NAME, object_name, content_type="image/png")
        # Remove the local image file if desired
        os.remove("random_color_image.png")
        return jsonify({"image_url": image_url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------------------------
# Run the Flask App
# ---------------------------
if __name__ == "__main__":
    app.run(debug=True)
