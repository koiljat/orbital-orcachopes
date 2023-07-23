import qrcode

data = "https://t.me/ORCAChopes_bot?start=darts"

# Generate QR code
qr = qrcode.QRCode(
    version=1,
    error_correction=qrcode.constants.ERROR_CORRECT_L,
    box_size=10,
    border=4,
)
qr.add_data(data)
qr.make(fit=True)
img = qr.make_image()
img.save("darts_qr_code.png")
