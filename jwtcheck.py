import jwt

token = "AAAI-WFS-8c8d194b-78e7-4878-b881-8a3b39cd9479"
payload = jwt.decode(token, options={"verify_signature": False})
print(payload)
