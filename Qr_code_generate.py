import qrcode
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
import os
import json
from datetime import datetime

# ------------------ CONFIGURATION ------------------
products = [
    {
        "name": "Rapidene 500mg",
        "price": "Rs. 150",
        "mfd": "2025-07-15",
        "exp": "2027-01-15",
        "prefix": "RAPIDENE",
        "count": 10,  # Reduced for testing
    },
    {
        "name": "Bisoprolol 2.5mg",
        "price": "Rs. 350",
        "mfd": "2025-05-10",
        "exp": "2026-05-10",
        "prefix": "BISOPROLOL",
        "count": 5,
    },
    {
        "name": "Domperidone 500mg",
        "price": "Rs. 150",
        "mfd": "2025-06-08",
        "exp": "2026-06-08",
        "prefix": "DOMPERIDONE",
        "count": 8,
    },
    {
        "name": "Azee 500mg",
        "price": "Rs. 400",
        "mfd": "2025-07-25",
        "exp": "2027-06-25",
        "prefix": "AZEE",
        "count": 6,
    },
    {
        "name": "Pantonix 20mg",
        "price": "Rs. 180",
        "mfd": "2025-06-20",
        "exp": "2026-06-20",
        "prefix": "PANTONIX",
        "count": 7,
    }
]

output_dir = "qr_images"
os.makedirs(output_dir, exist_ok=True)

# ------------------ PDF SETUP ------------------
pdf_filename = "product_qrcodes.pdf"
c = canvas.Canvas(pdf_filename, pagesize=A4)
page_width, page_height = A4

# Enhanced Layout configuration (10x10 for better spacing)
cols = 10  # Reduced from 12 for better spacing
rows = 10  # Reduced from 12 for better spacing
qr_size_mm = 16  # Slightly larger for better scanning
spacing_x = 18 * mm  # More horizontal space between QR codes
spacing_y = 24 * mm  # More vertical space (enough for QR + text without overlap)

start_x = 12 * mm
start_y = page_height - 15 * mm - qr_size_mm * mm


def generate_qr_image(data, filename):
    """Generate QR code image"""
    qr = qrcode.QRCode(
        version=2,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=3,  # Increased for better quality
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    path = os.path.join(output_dir, f"{filename}.png")
    qr_img.save(path)
    return path


def generate_inventory_json():
    """Generate JSON file for mobile app import with proper numeric values"""
    inventory_data = []

    for product in products:
        for i in range(1, product["count"] + 1):
            product_no = f"{product['prefix']}-{i:03d}"

            # Convert price string to number (remove "Rs. " and convert to float)
            price_clean = float(product['price'].replace('Rs. ', '').strip())

            inventory_item = {
                "productCode": product_no,
                "name": product["name"],
                "price": price_clean,
                "wholesalePrice": price_clean * 0.8,  # 20% less than retail
                "quantity": 1,
                "lowStockThreshold": 10,
                "category": "PHARMA",
                "manufactureDate": product["mfd"],
                "expiryDate": product["exp"],
                "createdAt": datetime.now().isoformat()
            }
            inventory_data.append(inventory_item)

    # Save JSON file
    json_path = "inventory_import.json"
    with open(json_path, "w", encoding='utf-8') as f:
        json.dump(inventory_data, f, indent=2, ensure_ascii=False)

    print(f"[✓] JSON created: {json_path} with {len(inventory_data)} products")
    return json_path, inventory_data


# ------------------ MAIN GENERATION ------------------
print("🚀 Starting QR Code Generation...")
print("=" * 50)

# Generate inventory JSON first
json_path, inventory_data = generate_inventory_json()

total_qr_count = 0

for product_index, product in enumerate(products):
    print(f"📦 Generating QR codes for: {product['name']}")

    # Start each product type on a NEW PAGE
    if product_index > 0:
        c.showPage()
        print(f"   📄 New page started for {product['name']}")

    count = 0
    for i in range(1, product["count"] + 1):
        product_no = f"{product['prefix']}-{i:03d}"

        # Your exact format: Pipe-delimited single-line QR data
        data = f"{product['name']}|{product['price']}|{product['mfd']}|{product['exp']}|{product_no}"

        image_filename = generate_qr_image(data, product_no)

        col = count % cols
        row = (count // cols) % rows

        x = start_x + col * spacing_x
        y = start_y - row * spacing_y

        # Draw QR code with proper spacing
        c.drawImage(image_filename, x, y, qr_size_mm * mm, qr_size_mm * mm)

        # Draw text below QR with proper spacing to avoid overlap
        text_y = y - 3 * mm  # Increased space between QR and text
        c.setFont("Helvetica", 6)  # Slightly larger font

        # Truncate product name if too long (with better handling)
        display_name = product['name']
        if len(display_name) > 16:  # Reduced for better fit
            display_name = display_name[:15] + "…"

        # Draw product name (centered below QR)
        text_width = c.stringWidth(display_name, "Helvetica", 6)
        text_x = x + (qr_size_mm * mm - text_width) / 2
        c.drawString(text_x, text_y, display_name)

        # Draw price with proper spacing
        price_text = f"Price: {product['price']}"
        price_width = c.stringWidth(price_text, "Helvetica", 5)
        price_x = x + (qr_size_mm * mm - price_width) / 2
        c.setFont("Helvetica", 5)
        c.drawString(price_x, text_y - 4 * mm, price_text)  # Increased spacing

        count += 1
        total_qr_count += 1

        # Start new page if grid is full (only for current product type)
        if count % (cols * rows) == 0 and count < product["count"]:
            c.showPage()
            print(f"   📄 Continuing {product['name']} on new page...")
            count = 0  # Reset count for new page of same product

    print(f"   ✅ Generated {product['count']} QR codes for {product['name']}")

# ------------------ SAVE PDF ------------------
c.save()
print("=" * 50)
print(f"[✓] PDF created: {pdf_filename}")
print(f"[✓] Total QR codes generated: {total_qr_count}")
print(f"[✓] JSON file created: {json_path}")

# Show next steps
print("\n📋 NEXT STEPS:")
print("1. 📱 MOBILE APP: Copy content from inventory_import.json to QR Import screen")
print("2. 🖨️  PRINT: Print product_qrcodes.pdf on sticker paper")
print("3. 🔗 APPLY: Stick QR codes on your products")
print("4. 💻 SCAN: Use web POS to scan QR codes!")
print("=" * 50)

# Show sample of generated data
print("\n📊 SAMPLE DATA:")
print("QR Code Content Format: Name|Price|MFD|EXP|ProductCode")
print("Example: Rapidene 500mg|Rs. 150|2025-07-15|2027-01-15|RAPIDENE-001")
print(f"\nTotal products in JSON: {len(inventory_data)}")