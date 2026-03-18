"""
运行一次即可创建管理员账号
python init_admin.py
"""
import json, os, bcrypt

USERS_FILE = "users.json"
USERNAME   = "admin"
PASSWORD   = "123456"

users = {}
if os.path.exists(USERS_FILE):
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        users = json.load(f)

hashed = bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt()).decode()
users[USERNAME] = {"password": hashed}

with open(USERS_FILE, "w", encoding="utf-8") as f:
    json.dump(users, f, ensure_ascii=False, indent=2)

print(f"✅ 管理员账号已创建：{USERNAME} / {PASSWORD}")
