import qrcode

# Adresse du site web
website = "https://www.omarabedelkader.com"

# Génération du QR code
qr = qrcode.QRCode(
    version=1,
    error_correction=qrcode.constants.ERROR_CORRECT_H,
    box_size=10,
    border=4,
)

qr.add_data(website)
qr.make(fit=True)

# Création de l'image
image = qr.make_image(fill_color="black", back_color="white")

# Enregistrement
image.save("qrcode_website.png")

print("QR code généré : qrcode_website.png")