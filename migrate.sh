#!/bin/bash

# X-UI to Marzban Migration Script
# یک خطی: bash <(curl -Ls https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/migrate.sh)

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}🚀 X-UI to Marzban Migration Script${NC}"
echo -e "${BLUE}═══════════ Designed by Javad Wolf ═══════════${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"

# بررسی وجود Python3
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 نصب نیست!${NC}"
    echo -e "${YELLOW}📦 در حال نصب Python3...${NC}"
    apt update -qq && apt install -y python3 python3-pip
fi

# بررسی وجود pip
if ! command -v pip3 &> /dev/null; then
    apt install -y python3-pip
fi

# نصب پیش‌نیازها
echo -e "${YELLOW}📦 در حال نصب پیش‌نیازها...${NC}"
pip3 install requests urllib3 -q

# ایجاد اسکریپت پایتون موقت
cat > /tmp/xui_to_marzban.py << 'EOF'
import os
import sys
import sqlite3
import json
import requests
import urllib3
import time
from datetime import datetime

urllib3.disable_warnings()

def find_xui_db():
    paths = ['x-ui.db', '/etc/x-ui/x-ui.db', '/root/x-ui.db', './x-ui.db']
    for p in paths:
        if os.path.exists(p):
            return p
    return None

def main():
    print("\n" + "="*60)
    print("🚀 X-UI to Marzban Migration Script")
    print("="*60)
    
    # پیدا کردن دیتابیس
    db_path = find_xui_db()
    if not db_path:
        print("❌ فایل دیتابیس X-UI پیدا نشد!")
        print("   لطفاً فایل x-ui.db را در پوشه فعلی قرار دهید")
        return
    
    print(f"✅ دیتابیس پیدا شد: {db_path}")
    
    # گرفتن اطلاعات مرزبان
    print("\n" + "="*60)
    print("🔐 تنظیمات پنل مرزبان")
    print("="*60)
    
    domain = input("آدرس مرزبان (مثال: panel.example.com): ").strip()
    port = input("پورت مرزبان [443]: ").strip()
    port = int(port) if port else 443
    use_https = input("استفاده از HTTPS؟ (y/n) [y]: ").strip().lower() != 'n'
    username = input("نام کاربری ادمین: ").strip()
    password = input("رمز عبور ادمین: ").strip()
    
    protocol = "https" if use_https else "http"
    
    # اتصال به مرزبان
    print("\n🔐 در حال اتصال به مرزبان...")
    login_url = f"{protocol}://{domain}:{port}/api/admin/token"
    
    try:
        resp = requests.post(login_url, data={'username': username, 'password': password}, verify=False, timeout=30)
        if resp.status_code != 200:
            print(f"❌ خطا در اتصال: {resp.status_code}")
            return
        token = resp.json().get('access_token')
        print("✅ اتصال موفق بود")
    except Exception as e:
        print(f"❌ خطا: {e}")
        return
    
    # استخراج کاربران
    print("\n📡 استخراج کاربران از دیتابیس...")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    c.execute("SELECT email, uuid FROM clients")
    clients = dict(c.fetchall())
    
    c.execute("SELECT email, up, down, total FROM client_traffics WHERE enable = 1")
    traffics = c.fetchall()
    conn.close()
    
    users = []
    for email, up, down, total in traffics:
        if email and email in clients:
            used = up + down
            rem = total - used if total > 0 else 0
            if total == 0:
                limit = 0
            elif rem > 0:
                limit = rem
            else:
                limit = 1073741824  # 1GB
            users.append({'email': email, 'uuid': clients[email], 'limit': limit})
    
    if not users:
        print("❌ هیچ کاربر فعالی یافت نشد!")
        return
    
    print(f"\n📊 {len(users)} کاربر برای انتقال آماده هستند")
    
    # دریافت اینباندها
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    inb_url = f"{protocol}://{domain}:{port}/api/inbounds"
    resp = requests.get(inb_url, headers=headers, verify=False)
    inbounds = resp.json()
    
    selected = {}
    for proto, items in inbounds.items():
        if items and proto == 'vless':
            selected['vless'] = [i.get('tag') for i in items]
    
    if not selected:
        print("❌ اینباند VLESS یافت نشد!")
        return
    
    print(f"✅ اینباندها: {selected['vless']}")
    
    # تأیید نهایی
    confirm = input(f"\n⚠️ {len(users)} کاربر منتقل می‌شوند. ادامه؟ (y/n): ").strip().lower()
    if confirm != 'y':
        print("لغو شد.")
        return
    
    # انتقال
    print("\n🚀 در حال انتقال...")
    success = 0
    create_url = f"{protocol}://{domain}:{port}/api/user"
    
    for i, u in enumerate(users, 1):
        print(f"[{i}/{len(users)}] {u['email']}...", end=" ")
        data = {
            "username": u['email'],
            "proxies": {"vless": {"id": u['uuid'], "flow": "xtls-rprx-vision"}},
            "inbounds": selected,
            "expire": 0,
            "data_limit": u['limit'],
            "data_limit_reset_strategy": "no_reset",
            "status": "active"
        }
        try:
            resp = requests.post(create_url, json=data, headers=headers, verify=False, timeout=30)
            if resp.status_code == 200:
                print("✅")
                success += 1
            elif resp.status_code == 409:
                new_name = f"{u['email']}_{int(time.time())%10000}"
                data['username'] = new_name
                resp = requests.post(create_url, json=data, headers=headers, verify=False)
                if resp.status_code == 200:
                    print(f"✅ ({new_name})")
                    success += 1
                else:
                    print("❌")
            else:
                print(f"❌ ({resp.status_code})")
        except:
            print("❌")
        time.sleep(0.3)
    
    print("\n" + "="*60)
    print(f"📊 نتیجه: ✅ {success} موفق | ❌ {len(users)-success} ناموفق")
    print("="*60)

if __name__ == "__main__":
    main()
EOF

# اجرای اسکریپت پایتون
python3 /tmp/xui_to_marzban.py

# پاک کردن فایل موقت
rm -f /tmp/xui_to_marzban.py

echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
