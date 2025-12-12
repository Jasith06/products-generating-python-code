import qrcode
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
import os
import json
from datetime import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import pickle

# Google Drive API Setup
SCOPES = ['https://www.googleapis.com/auth/drive.file']


def get_drive_service():
    """Authenticate and return Google Drive service"""
    creds = None

    # Token file stores user's access and refresh tokens
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # If no valid credentials, let user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        # Save credentials for next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return build('drive', 'v3', credentials=creds)


def upload_to_drive(filename, filepath, folder_id=None):
    """Upload file to Google Drive and return shareable link"""
    try:
        service = get_drive_service()

        file_metadata = {
            'name': filename,
            'mimeType': 'application/json'
        }

        if folder_id:
            file_metadata['parents'] = [folder_id]

        media = MediaFileUpload(filepath, mimetype='application/json')

        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()

        # Make file publicly accessible (read-only)
        service.permissions().create(
            fileId=file['id'],
            body={'type': 'anyone', 'role': 'reader'}
        ).execute()

        # Get direct download link
        download_link = f"https://drive.google.com/uc?export=download&id={file['id']}"

        print(f"✅ Uploaded to Google Drive!")
        print(f"📎 File ID: {file['id']}")
        print(f"🔗 Download Link: {download_link}")

        return file['id'], download_link

    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return None, None


def generate_link_qr_code(download_link, output_filename="gdrive_qrcode.png"):
    """Generate QR code for Google Drive download link"""
    try:
        qr = qrcode.QRCode(
            version=4,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(download_link)
        qr.make(fit=True)
        
        qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        
        # Add some text below the QR code
        from PIL import ImageDraw, ImageFont
        
        # Create a larger image to accommodate text
        padding = 50
        new_height = qr_img.size[1] + padding
        new_img = Image.new('RGB', (qr_img.size[0], new_height), 'white')
        new_img.paste(qr_img, (0, 0))
        
        draw = ImageDraw.Draw(new_img)
        
        # Try to use a font, fallback to default if not available
        try:
            font = ImageFont.truetype("arial.ttf", 16)
        except:
            font = ImageFont.load_default()
        
        # Add text below QR code
        text = "Scan to download inventory"
        text_width = draw.textlength(text, font=font)
        text_x = (qr_img.size[0] - text_width) // 2
        text_y = qr_img.size[1] + 10
        
        draw.text((text_x, text_y), text, fill="black", font=font)
        
        new_img.save(output_filename)
        print(f"✅ QR code for download link saved as: {output_filename}")
        
        return output_filename
        
    except Exception as e:
        print(f"❌ Failed to generate link QR code: {e}")
        return None


# ------------------ CONFIGURATION ------------------
products = [
    {
        "name": "Rapidene 500mg",
        "category": "PHARMA",
        "price": "Rs. 150",
        "mfd": "2025-07-15",
        "exp": "2027-01-15",
        "prefix": "RAPIDENE",
        "count": 3,
    },
    {
        "name": "Bisoprolol 2.5mg",
        "category": "PHARMA",
        "price": "Rs. 350",
        "mfd": "2025-05-10",
        "exp": "2026-05-10",
        "prefix": "BISOPROLOL",
        "count": 2,
    },
]

output_dir = "qr_images"
os.makedirs(output_dir, exist_ok=True)

# ------------------ PDF SETUP ------------------
pdf_filename = "product_qrcodes.pdf"
c = canvas.Canvas(pdf_filename, pagesize=A4)
page_width, page_height = A4

cols = 10
rows = 10
qr_size_mm = 16
spacing_x = 18 * mm
spacing_y = 24 * mm
start_x = 12 * mm
start_y = page_height - 15 * mm - qr_size_mm * mm


def generate_qr_image(data, filename):
    """Generate QR code image"""
    qr = qrcode.QRCode(
        version=2,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=3,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    path = os.path.join(output_dir, f"{filename}.png")
    qr_img.save(path)
    return path


def generate_inventory_json():
    """Generate JSON file for mobile app import"""
    inventory_data = []

    for product in products:
        for i in range(1, product["count"] + 1):
            product_no = f"{product['prefix']}-{i:03d}"
            price_clean = float(product['price'].replace('Rs. ', '').strip())

            inventory_item = {
                "productCode": product_no,
                "name": product["name"],
                "price": price_clean,
                "wholesalePrice": price_clean * 0.8,
                "quantity": 1,
                "lowStockThreshold": 10,
                "category": product["category"],
                "manufactureDate": product["mfd"],
                "expiryDate": product["exp"],
                "createdAt": datetime.now().isoformat()
            }
            inventory_data.append(inventory_item)

    # Save JSON file locally
    json_path = "inventory_import.json"
    with open(json_path, "w", encoding='utf-8') as f:
        json.dump(inventory_data, f, indent=2, ensure_ascii=False)

    print(f"✅ JSON created: {json_path} with {len(inventory_data)} products")
    return json_path, inventory_data


# ------------------ MAIN GENERATION ------------------
print("🚀 Starting QR Code Generation with Google Drive Upload...")
print("=" * 50)

# Generate inventory JSON
json_path, inventory_data = generate_inventory_json()

# Generate QR codes and PDF
total_qr_count = 0
for product_index, product in enumerate(products):
    print(f"📦 Generating QR codes for: {product['name']}")

    if product_index > 0:
        c.showPage()

    count = 0
    for i in range(1, product["count"] + 1):
        product_no = f"{product['prefix']}-{i:03d}"
        data = f"{product['name']}|{product['price']}|{product['mfd']}|{product['exp']}|{product_no}"

        image_filename = generate_qr_image(data, product_no)

        col = count % cols
        row = (count // cols) % rows
        x = start_x + col * spacing_x
        y = start_y - row * spacing_y

        c.drawImage(image_filename, x, y, qr_size_mm * mm, qr_size_mm * mm)

        text_y = y - 3 * mm
        c.setFont("Helvetica", 6)
        display_name = product['name'][:15] + "…" if len(product['name']) > 16 else product['name']

        text_width = c.stringWidth(display_name, "Helvetica", 6)
        text_x = x + (qr_size_mm * mm - text_width) / 2
        c.drawString(text_x, text_y, display_name)

        price_text = f"Price: {product['price']}"
        price_width = c.stringWidth(price_text, "Helvetica", 5)
        price_x = x + (qr_size_mm * mm - price_width) / 2
        c.setFont("Helvetica", 5)
        c.drawString(price_x, text_y - 4 * mm, price_text)

        count += 1
        total_qr_count += 1

        if count % (cols * rows) == 0 and count < product["count"]:
            c.showPage()
            count = 0

    print(f"   ✅ Generated {product['count']} QR codes")

c.save()
print(f"✅ PDF created: {pdf_filename}")

# Upload to Google Drive
print("\n📤 Uploading to Google Drive...")
file_id, download_link = upload_to_drive(
    filename=f"inventory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
    filepath=json_path
)

if download_link:
    # Generate QR code for the download link (4th output)
    print("\n🔳 Generating QR code for download link...")
    qr_filename = generate_link_qr_code(download_link)
    
    if qr_filename:
        print(f"✅ QR code image saved as: {qr_filename}")
        
        # Display the QR code if possible
        try:
            img = Image.open(qr_filename)
            img.show()
            print("📱 QR code image opened for preview!")
        except:
            print("💡 QR code image saved. Open it manually to view.")
    
    # Save the link to a text file for easy access
    with open("gdrive_link.txt", "w") as f:
        f.write(f"Google Drive Link:\n{download_link}\n\n")
        f.write(f"File ID: {file_id}\n")
        if qr_filename:
            f.write(f"QR Code Image: {qr_filename}\n")

    print("\n" + "=" * 50)
    print("📋 SETUP COMPLETE!")
    print("=" * 50)
    print(f"📱 Use this link in your mobile app:")
    print(f"   {download_link}")
    print(f"\n🔳 QR Code for the link saved as: {qr_filename}")
    print(f"\n💡 Copy this link and add it to your mobile app's")
    print(f"   QR Import screen for direct download!")
    print(f"💡 Or scan the QR code from: {qr_filename}")
else:
    print("\n⚠️ Google Drive upload failed. Using manual method.")
    print("📋 Copy content from: inventory_import.json")
