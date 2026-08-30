import os
from PIL import Image, ImageDraw, ImageFont

def create_prose_document(title: str, lines: list) -> Image.Image:
    """
    Helper to render a clean A4-like image with legal prose sentences.
    """
    # 800x1000 canvas
    img = Image.new("RGB", (800, 1000), color="white")
    draw = ImageDraw.Draw(img)
    
    try:
        font_title = ImageFont.truetype("arial.ttf", 24)
        font_header = ImageFont.truetype("arial.ttf", 16)
        font_body = ImageFont.truetype("arial.ttf", 14)
    except IOError:
        font_title = ImageFont.load_default()
        font_header = ImageFont.load_default()
        font_body = ImageFont.load_default()
        
    # Draw border
    draw.rectangle([20, 20, 780, 980], outline="black", width=3)
    
    # Draw title and header
    draw.text((400, 50), title, fill="black", anchor="ms", font=font_title)
    draw.text((400, 85), "OFFICIAL REGISTRY DOCUMENT (PROSE DEMO)", fill="gray", anchor="ms", font=font_header)
    draw.line([40, 100, 760, 100], fill="black", width=2)
    
    # Draw lines of prose
    y_offset = 140
    for line in lines:
        if line == "---":
            draw.line([40, y_offset, 760, y_offset], fill="gray", width=1)
            y_offset += 25
        else:
            # Simple word-wrapping to fit the width (max 700px)
            words = line.split()
            current_line = []
            for word in words:
                current_line.append(word)
                test_str = " ".join(current_line)
                # Estimate text width based on character length
                if len(test_str) * 8 > 680:
                    draw.text((60, y_offset), " ".join(current_line[:-1]), fill="black", font=font_body)
                    y_offset += 25
                    current_line = [word]
            if current_line:
                draw.text((60, y_offset), " ".join(current_line), fill="black", font=font_body)
                y_offset += 35
                
    return img

def main():
    os.makedirs("data/samples", exist_ok=True)
    
    print("Generating Sale Deed Prose Document...")
    sale_deed_lines = [
        "THIS DEED OF SALE is made and executed on this 15-06-2025 at Kurukshetra.",
        "BETWEEN Ramesh Kumar, resident of House No 12, Rampur, hereinafter called the Vendor/Seller of the first part,",
        "AND Suresh Kumar, resident of House No 45, Kurukshetra, hereinafter called the Purchaser/Buyer of the second part.",
        "WHEREAS the Vendor is the sole and absolute owner of the agricultural land situated at Village Rampur, Tehsil Thanesar, District Kurukshetra, under Survey Number 124/3, measuring an Area of 2.45 Acres.",
        "NOW THIS DEED OF SALE WITNESSETH that in consideration of a sum of Rs. 8,50,000 paid as sale consideration, the receipt of which is hereby acknowledged, the Vendor hereby sells, transfers, and conveys all rights, titles, and interests in the said property to the Purchaser.",
        "IN WITNESS WHEREOF, the parties hereto have signed this deed.",
        "---",
        "Property Location: Plot 14, Sector 5, Rampur.",
        "Seller Address: House No 12, Rampur.",
        "Buyer Address: House No 45, Kurukshetra.",
        "Registration Details: Volume 12, Page 45, Document Registration Number 543/2025."
    ]
    sale_img = create_prose_document("SALE DEED OF LAND TITLE", sale_deed_lines)
    sale_img.save("data/samples/sale_deed_prose.png")
    print("Saved to data/samples/sale_deed_prose.png")
    
    print("\nGenerating Partition Deed Prose Document...")
    partition_deed_lines = [
        "THIS DEED OF PARTITION is made and executed on this 01-03-2025 at Kurukshetra,",
        "among Ramesh Kumar, Suresh Kumar, and Priya Kumar, who are co-owners of the land.",
        "The total area of the jointly held property is 3.10 Acres located in Village Kalyanpur, District Kurukshetra, registered under Survey Number 87.",
        "WHEREAS the parties have agreed to divide the property among themselves according to their mutual shares as follows:",
        "Ramesh Kumar is allotted a share allocation of 1.05 acres.",
        "Suresh Kumar is allotted a share allocation of 1.05 acres.",
        "Priya Kumar is allotted a share allocation of 1.00 acres.",
        "The total party count is 3 co-owners.",
        "---",
        "Property Description: Divided into three equal portions bounded by north, south, and main road.",
        "Registration details: Book 1, Volume 4, Partition Deed Registration Number 876/2025."
    ]
    partition_img = create_prose_document("DEED OF PARTITION", partition_deed_lines)
    partition_img.save("data/samples/partition_deed_prose.png")
    print("Saved to data/samples/partition_deed_prose.png")

if __name__ == "__main__":
    main()

