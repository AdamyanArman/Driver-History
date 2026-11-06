import os
from dotenv import load_dotenv
from werkzeug.security import check_password_hash, generate_password_hash

# Բեռնում ենք .env-ը
load_dotenv()

user = os.getenv("WEB_USERNAME")
pw_hash = os.getenv("WEB_PASSWORD_HASH")

print("--- ՍՏՈՒԳՈՒՄ ԵՆՔ .ENV ՖԱՅԼԸ ---")
print(f"Մուտքանունը .env-ում: '{user}'")

if pw_hash:
    print(f"Հեշը .env-ում առկա է, սկսվում է այսպես՝ '{pw_hash[:20]}...'")
else:
    print("❌ ՍԽԱԼ. Հեշը դատարկ է (None)։")

print("-" * 30)
test_password = input("Մուտքագրեք ձեր սովորական գաղտնաբառը (որով փորձում եք մտնել կայք)՝ ")

if pw_hash and check_password_hash(pw_hash, test_password):
    print("\n✅ ԱՄԵՆ ԻՆՉ ՃԻՇՏ Է։ Գաղտնաբառը համապատասխանում է հեշին։")
    print("Խնդիրը հավանաբար բրաուզերի մեջ է (մաքրեք cache-ը կամ փորձեք Incognito ռեժիմով):")
else:
    print("\n❌ ՍԽԱԼ։ Գաղտնաբառը ՉԻ համապատասխանում .env-ի հեշին։")
    print("Եկեք ստեղծենք ՆՈՐ հեշ հենց այս գաղտնաբառի համար։")
    new_hash = generate_password_hash(test_password)
    print("\nՊատճենեք այս նոր հեշը և դրեք ձեր .env ֆայլում (առանց չակերտների և բացատների)՝\n")
    print(f"WEB_PASSWORD_HASH={new_hash}")