import qrcode

# Adresse email du destinataire
email = "omar.abedelkader@inria.fr"

# Création du lien mailto sans sujet ni corps
mailto = f"mailto:{email}"

# Génération du QR code
qr = qrcode.QRCode(
    version=1,
    error_correction=qrcode.constants.ERROR_CORRECT_H,
    box_size=10,
    border=4,
)

qr.add_data(mailto)
qr.make(fit=True)

# Création de l'image
image = qr.make_image(fill_color="black", back_color="white")

# Enregistrement
image.save("qrcode_email.png")

print("QR code généré : qrcode_email.png")