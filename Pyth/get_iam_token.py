import time
import jwt  # pyjwt
import requests
import json

# Загрузи ключ из key.json
with open('key.json.py', 'r') as f:
    key_data = json.load(f)

service_account_id = key_data["service_account_id"]
key_id = key_data["id"]
private_key = key_data["private_key"]

# Создание JWT
now = int(time.time())
payload = {
    "aud": "https://iam.api.cloud.yandex.net/iam/v1/tokens",
    "iss": service_account_id,
    "iat": now,
    "exp": now + 360,
}

encoded_jwt = jwt.encode(
    payload,
    private_key,
    algorithm="PS256",
    headers={"kid": key_id},
)

# Запрос IAM-токена
response = requests.post(
    "https://iam.api.cloud.yandex.net/iam/v1/tokens",
    json={"jwt": encoded_jwt},
)

if response.status_code == 200:
    iam_token = response.json()["iamToken"]
    print("✅ IAM Token:", iam_token)
else:
    print("❌ Ошибка:", response.text)