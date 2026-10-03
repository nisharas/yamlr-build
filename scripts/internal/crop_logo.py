import os

from PIL import Image

input_path = r"D:\yamlr\assets\branding\yamlr_logo_white_bg.png"
output_path = r"D:\yamlr\vscode\extension-logo.png"

if os.path.exists(input_path):
    with Image.open(input_path) as img:
        width, height = img.size
        # Make it square
        size = min(width, height)
        left = (width - size) // 2
        top = (height - size) // 2
        right = (width + size) // 2
        bottom = (height + size) // 2

        img_cropped = img.crop((left, top, right, bottom))
        # Resize to 128x128 for VS Code
        img_final = img_cropped.resize((128, 128), Image.Resampling.LANCZOS)
        img_final.save(output_path, "PNG")
        print(f"✅ Logo square-cropped and saved to {output_path}")
else:
    print(f"❌ Input file not found: {input_path}")
