from cryptography.fernet import Fernet
import json

# 1. Ստեղծում ենք Ձեր եզակի Գլխավոր Բանալին
key = Fernet.generate_key()
cipher = Fernet(key)

print("=== ՁԵՐ ԳԼԽԱՎՈՐ ԲԱՆԱԼԻՆ (ENCRYPTION_KEY) ===")
print(key.decode())
print("============================================\n")

# 2. Ձեր իրական տվյալները, որոնք ուզում եք թաքցնել
real_login_url = "https://kaisersupermarket.am/driver/api/login/"
real_history_url = "https://kaisersupermarket.am/driver/api/history/"
psw="Drivers_Hisoryyy"

# Ուշադրություն՝ այստեղ դնում եք Ձեր ամբողջական JSON-ը
real_drivers_json = '{"1": {"login": "Armen@ks.am", "password": "Armen.222", "display_name": "Armen"}, "2": {"login": "Davit@ks.am", "password": "Davit.000", "display_name": "Davit"}, "3": {"login": "Syoma@ks.am", "password": "Syoma.000", "display_name": "Syoma"}, "4": {"login": "Hayk@ks.am", "password": "Hayk.123", "display_name": "Hayk"}, "5": {"login": "Karen@ks.am", "password": "Karen.888", "display_name": "Karen"}, "6": {"login": "Seroj@ks.am", "password": "Seroj.111", "display_name": "Seroj"}}'

# 3. Գաղտնագրում ենք դրանք
enc_login = cipher.encrypt(real_login_url.encode()).decode()
enc_history = cipher.encrypt(real_history_url.encode()).decode()
enc_drivers = cipher.encrypt(real_drivers_json.encode()).decode()
enc_psw=cipher.encrypt(psw.encode()).decode()


print("LOGIN_URL_ENCRYPTED=", enc_login)
print("HISTORY_URL_ENCRYPTED=", enc_history)
print("DRIVERS_JSON_ENCRYPTED=", enc_drivers)
print("psw", enc_psw)