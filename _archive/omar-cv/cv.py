import qrcode
from PIL import Image

# Create a QR code
qr_data = "http://omarabedelkader.github.io/files/cv-en.pdf"  # The URL or data to encode in the QR code
qr = qrcode.QRCode(
    version=1,
    error_correction=qrcode.constants.ERROR_CORRECT_L,
    box_size=10,
    border=4,
)
qr.add_data(qr_data)
qr.make(fit=True)

# Create the image for the QR code
qr_image = qr.make_image(fill="black", back_color="white")

# Convert the QR image to an editable format
qr_image = qr_image.convert("RGB")

# Save the image
qr_image.save("qr_code_cv.png")

# Optionally display the image
qr_image.show()
