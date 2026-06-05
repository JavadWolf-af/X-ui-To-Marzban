#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
X-UI to Marzban Migration Script
انتقال خودکار کاربران از X-UI به مرزبان
"""

import os
import sys
import subprocess
import importlib
from datetime import datetime

def install_requirements():
    """نصب پیش‌نیازهای مورد نیاز"""
    requirements = ['requests', 'urllib3']
    missing = []
    
    for req in requirements:
        try:
            importlib.import_module(req)
        except ImportError:
            missing.append(req)
    
    if missing:
        print(f"\n📦 در حال نصب پیش‌نیازهای缺失: {', '.join(missing)}")
        for req in missing:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", req])
                print(f"   ✅ {req} نصب شد")
            except:
                print(f"   ❌ خطا در نصب {req}")
                return False
    return True

def find_xui_db():
    """پیدا کردن فایل دیتابیس X-UI"""
    possible_paths = [
        'x-ui.db',
        '/etc/x-ui/x-ui.db',
        '/root/x-ui.db',
        './x-ui.db'
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None

def get_marzban_config():
    """گرفتن اطلاعات پنل مرزبان از کاربر"""
    print("\n" + "="*60)
    print("🔐 تنظیمات پنل مرزبان")
    print("="*60)
    
    config = {}
    
    config['domain'] = input("آدرس دامنه یا IP مرزبان (مثال: panel.example.com): ").strip()
    config['port'] = input("پورت مرزبان (معمولاً 443 یا 8000) [پیش‌فرض: 443]: ").strip()
    config['port'] = int(config['port']) if config['port'] else 443
    
    protocol = input("استفاده از HTTPS؟ (y/n) [پیش‌فرض: y]: ").strip().lower()
    config['https'] = protocol != 'n'
    
    config['username'] = input("نام کاربری ادمین مرزبان: ").strip()
    config['password'] = input("رمز عبور ادمین مرزبان: ").strip()
    
    return config

def show_migration_summary(users, unlimited, limited, exhausted):
    """نمایش خلاصه انتقال"""
    print("\n" + "="*60)
    print("📊 خلاصه کاربران برای انتقال")
    print("="*60)
    print(f"   ✅ کاربران فعال: {len(users)}")
    print(f"   ♾️  کاربران نامحدود: {len(unlimited)}")
    print(f"   📦 کاربران با حجم باقیمانده: {len(limited)}")
    print(f"   🔄 کاربران با حجم تمام شده: {len(exhausted)}")
    
    if limited:
        print("\n📋 نمونه کاربران با حجم باقیمانده:")
        for user in limited[:3]:
            print(f"   - {user['email']}: {user['remaining_gb']:.2f} GB")

def main():
    print("="*60)
    print("🚀 X-UI to Marzban Migration Script")
    print("   انتقال خودکار کاربران به مرزبان")
    print("="*60)
    
    # نصب پیش‌نیازها
    if not install_requirements():
        print("❌ خطا در نصب پیش‌نیازها. لطفاً دستی نصب کنید: pip install requests")
        return
    
    # وارد کردن ماژول‌ها بعد از نصب
    import sqlite3
    import json
    import requests
    import urllib3
    import time
    urllib3.disable_warnings()
    
    # پیدا کردن دیتابیس
    print("\n🔍 در حال جستجوی دیتابیس X-UI...")
    db_path = find_xui_db()
    if not db_path:
        print("❌ فایل دیتابیس X-UI پیدا نشد!")
        print("   لطفاً فایل x-ui.db را در پوشه فعلی قرار دهید")
        return
    
    print(f"✅ دیتابیس پیدا شد: {db_path}")
    
    # گرفتن اطلاعات مرزبان
    marzban = get_marzban_config()
    
    # اتصال به مرزبان و تست
    print("\n🔐 در حال اتصال به مرزبان...")
    protocol = "https" if marzban['https'] else "http"
    login_url = f"{protocol}://{marzban['domain']}:{marzban['port']}/api/admin/token"
    
    try:
        response = requests.post(login_url, 
                                data={'username': marzban['username'], 'password': marzban['password']},
                                verify=False, timeout=30)
        if response.status_code != 200:
            print(f"❌ خطا در اتصال به مرزبان: {response.status_code}")
            return
        token = response.json().get('access_token')
        print("✅ اتصال به مرزبان موفقیت‌آمیز بود")
    except Exception as e:
        print(f"❌ خطا در اتصال به مرزبان: {e}")
        return
    
    # استخراج کاربران از دیتابیس
    print("\n📡 در حال استخراج کاربران از دیتابیس...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # خواندن اطلاعات کاربران
    cursor.execute("SELECT email, uuid FROM clients")
    clients = dict(cursor.fetchall())
    
    cursor.execute("SELECT email, up, down, total FROM client_traffics WHERE enable = 1")
    traffics = cursor.fetchall()
    
    conn.close()
    
    # پردازش کاربران
    users = []
    unlimited = []
    limited = []
    exhausted = []
    
    for email, up, down, total_bytes in traffics:
        if not email or email not in clients:
            continue
        
        uuid = clients[email]
        used_bytes = up + down
        remaining_bytes = total_bytes - used_bytes if total_bytes > 0 else 0
        
        if total_bytes == 0:
            data_limit = 0
            status = 'unlimited'
            unlimited.append({'email': email})
        elif remaining_bytes > 0:
            data_limit = remaining_bytes
            status = 'limited'
            limited.append({'email': email, 'remaining_gb': remaining_bytes/(1024**3)})
        else:
            data_limit = 1 * 1024 * 1024 * 1024  # 1 GB
            status = 'exhausted'
            exhausted.append({'email': email})
        
        users.append({
            'email': email,
            'uuid': uuid,
            'data_limit': data_limit
        })
    
    if not users:
        print("❌ هیچ کاربر فعالی یافت نشد!")
        return
    
    # نمایش خلاصه
    show_migration_summary(users, unlimited, limited, exhausted)
    
    # گرفتن تأیید نهایی
    print("\n" + "="*60)
    confirm = input(f"\n⚠️ {len(users)} کاربر به مرزبان منتقل خواهند شد. ادامه می‌دهید؟ (y/n): ").strip().lower()
    if confirm != 'y':
        print("❌ عملیات لغو شد.")
        return
    
    # دریافت اینباندهای مرزبان
    print("\n📡 دریافت اینباندهای مرزبان...")
    inbounds_url = f"{protocol}://{marzban['domain']}:{marzban['port']}/api/inbounds"
    headers = {"Authorization": f"Bearer {token}", "accept": "application/json"}
    
    try:
        response = requests.get(inbounds_url, headers=headers, verify=False)
        inbounds = response.json()
        
        selected_inbounds = {}
        for protocol_type, items in inbounds.items():
            if items and protocol_type == 'vless':
                selected_inbounds['vless'] = [item.get('tag') for item in items]
        
        if not selected_inbounds:
            print("❌ اینباند VLESS در مرزبان یافت نشد!")
            print("   لطفاً ابتدا یک اینباند VLESS در مرزبان ایجاد کنید.")
            return
        
        print(f"✅ اینباندهای VLESS یافت شد: {selected_inbounds['vless']}")
    except Exception as e:
        print(f"❌ خطا در دریافت اینباندها: {e}")
        return
    
    # شروع انتقال
    print("\n" + "="*60)
    print("🚀 در حال انتقال کاربران...")
    print("="*60)
    
    success = 0
    fail = 0
    
    create_url = f"{protocol}://{marzban['domain']}:{marzban['port']}/api/user"
    
    for i, user in enumerate(users, 1):
        print(f"[{i}/{len(users)}] {user['email']}...", end=" ")
        
        data = {
            "username": user['email'],
            "proxies": {
                "vless": {
                    "id": user['uuid'],
                    "flow": "xtls-rprx-vision"
                }
            },
            "inbounds": selected_inbounds,
            "expire": 0,
            "data_limit": user['data_limit'],
            "data_limit_reset_strategy": "no_reset",
            "status": "active"
        }
        
        try:
            response = requests.post(create_url, json=data, headers=headers, verify=False, timeout=30)
            
            if response.status_code == 200:
                print("✅")
                success += 1
            elif response.status_code == 409:
                new_name = f"{user['email']}_{int(time.time())%10000}"
                data['username'] = new_name
                response = requests.post(create_url, json=data, headers=headers, verify=False)
                if response.status_code == 200:
                    print(f"✅ (تغییر نام: {new_name})")
                    success += 1
                else:
                    print(f"❌ (تکراری)")
                    fail += 1
            else:
                print(f"❌ ({response.status_code})")
                fail += 1
        except Exception as e:
            print(f"❌ (خطا)")
            fail += 1
        
        time.sleep(0.3)
    
    # گزارش نهایی
    print("\n" + "="*60)
    print("📊 گزارش نهایی:")
    print(f"   ✅ انتقال موفق: {success}")
    print(f"   ❌ انتقال ناموفق: {fail}")
    print(f"   📊 مجموع کاربران: {len(users)}")
    print("="*60)
    
    if success > 0:
        print("\n🎉 انتقال کاربران با موفقیت انجام شد!")
        print("   لطفاً پنل مرزبان را بررسی کنید.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ عملیات توسط کاربر متوقف شد.")
    except Exception as e:
        print(f"\n❌ خطای غیرمنتظره: {e}")
