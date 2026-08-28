import os
import random
from PIL import Image, ImageDraw, ImageFont

def create_base_document(title: str, lines: list) -> Image.Image:
    """
    Creates a base land record document image with text lines.
    """
    # 800x1000 canvas
    img = Image.new("RGB", (800, 1000), color="white")
    draw = ImageDraw.Draw(img)
    
    # Try using Arial, fallback to default font if not available
    try:
        font_title = ImageFont.truetype("arial.ttf", 28)
        font_header = ImageFont.truetype("arial.ttf", 20)
        font_body = ImageFont.truetype("arial.ttf", 18)
    except IOError:
        font_title = ImageFont.load_default()
        font_header = ImageFont.load_default()
        font_body = ImageFont.load_default()
        
    # Draw border
    draw.rectangle([20, 20, 780, 980], outline="black", width=3)
    
    # Draw title
    draw.text((400, 50), title, fill="black", anchor="ms", font=font_title)
    draw.text((400, 90), "OFFICIAL LAND RECORD REGISTRY (MOCK)", fill="gray", anchor="ms", font=font_header)
    draw.line([40, 110, 760, 110], fill="black", width=2)
    
    # Draw lines of text
    y_offset = 180
    for line in lines:
        if line == "---":
            draw.line([40, y_offset, 760, y_offset], fill="gray", width=1)
            y_offset += 30
        elif ":" in line:
            parts = line.split(":", 1)
            label, value = parts[0] + ":", parts[1].strip()
            # Draw label
            draw.text((80, y_offset), label, fill="black", font=font_body)
            # Draw value further to the right to test spatial neighbor detection
            draw.text((320, y_offset), value, fill="black", font=font_body)
            y_offset += 60
        else:
            draw.text((80, y_offset), line, fill="black", font=font_body)
            y_offset += 50
            
    return img

def apply_noise(img: Image.Image) -> Image.Image:
    """
    Applies blurring and pixel noise to simulate a poor-quality scan.
    """
    import numpy as np
    import cv2
    
    # Convert PIL to OpenCV format
    open_cv_image = np.array(img)
    # Convert RGB to BGR
    open_cv_image = open_cv_image[:, :, ::-1].copy()
    
    # Add salt and pepper noise
    row, col, ch = open_cv_image.shape
    s_vs_p = 0.5
    amount = 0.005
    out = np.copy(open_cv_image)
    
    # Salt mode
    num_salt = np.ceil(amount * open_cv_image.size * s_vs_p)
    coords = [np.random.randint(0, i - 1, int(num_salt)) for i in open_cv_image.shape]
    out[tuple(coords)] = 255

    # Pepper mode
    num_pepper = np.ceil(amount * open_cv_image.size * (1. - s_vs_p))
    coords = [np.random.randint(0, i - 1, int(num_pepper)) for i in open_cv_image.shape]
    out[tuple(coords)] = 0
    
    # Apply Gaussian Blur to simulate fading/fuzziness
    blurred = cv2.GaussianBlur(out, (3, 3), 0)
    
    # Convert BGR back to PIL RGB
    noisy_img = Image.fromarray(cv2.cvtColor(blurred, cv2.COLOR_BGR2RGB))
    return noisy_img

def main():
    os.makedirs("data/samples", exist_ok=True)
    
    print("Generating Document A (Clean, High Accuracy)...")
    doc_a_lines = [
        "District: Kurukshetra",
        "Tehsil: Thanesar",
        "Village: Rampur",
        "---",
        "Owner Name: Ramesh Kumar",
        "Survey Number: 124/3",
        "Area: 2.45 Acres"
    ]
    doc_a = create_base_document("STATE OF HARYANA", doc_a_lines)
    doc_a.save("data/samples/document_a.png")
    
    print("Generating Document B (Noisy, Low Quality Scan)...")
    doc_b_lines = [
        "District: Kurukshetra",
        "Tehsil: Thanesar",
        "Village: Rampur",
        "---",
        "Owner Name: Ramesh Kumar",
        "Survey Number: 124/3",
        "Area: 2.45 Acres"
    ]
    doc_b_clean = create_base_document("STATE OF HARYANA", doc_b_lines)
    try:
        doc_b = apply_noise(doc_b_clean)
    except Exception as e:
        print(f"Skipping noise application because OpenCV is not yet configured: {e}")
        doc_b = doc_b_clean
    doc_b.save("data/samples/document_b.png")
    
    print("Generating Document C (Missing Mandatory Fields)...")
    # Missing Survey Number and Village
    doc_c_lines = [
        "District: Kurukshetra",
        "Tehsil: Thanesar",
        "---",
        "Owner Name: Suresh Chandra",
        "Area: 1.25 Hectares"
    ]
    doc_c = create_base_document("STATE OF HARYANA", doc_c_lines)
    doc_c.save("data/samples/document_c.png")
    
    print("Generating Document D (Ambiguous/Conflicting Records)...")
    # Survey 87 is registered to Sunita Devi in Kalyanpur, but document lists Ramesh Kumar
    doc_d_lines = [
        "District: Kurukshetra",
        "Tehsil: Thanesar",
        "Village: Kalyanpur",
        "---",
        "Owner Name: Ramesh Kumar",
        "Survey Number: 87",
        "Area: 3.10 Acres"
    ]
    doc_d = create_base_document("STATE OF HARYANA", doc_d_lines)
    doc_d.save("data/samples/document_d.png")
    
    print("All mock documents generated successfully in data/samples/")

if __name__ == "__main__":
    main()
