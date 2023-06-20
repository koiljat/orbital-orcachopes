import qrcode

data = "https://t.me/ORCAChopes_bot?start=pool_table"

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
img.save("pool_table_qr_code.png")
