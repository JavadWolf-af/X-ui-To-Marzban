#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
X-UI to Marzban Migration Script (نسخه کامل با پشتیبانی از تاریخ انقضا)
انتقال خودکار کاربران از X-UI به مرزبان همراه با حجم باقیمانده و تاریخ انقضا
"""

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
    """پیدا کردن فایل دیتابیس X-UI"""
    paths = ['x-ui.db', '/etc/x-ui/x-ui.db', '/root/x-ui.db', './x-ui.db']
    for p in paths:
        if os.path.exists(p):
            return p
    return None

def get_marzban_config():
    """گرفتن اطلاعات پنل مرزبان از کاربر"""
    print("\n" + "="*60)
    print("🔐 تنظیمات پنل مرزبان")
    print("="*60)
    
    config = {}
    config['domain'] = input("آدرس مرزبان (مثال: panel.example.com): ").strip()
    config['port'] = input("پورت مرزبان [443]: ").strip()
    config['port'] = int(config['port']) if config['port'] else 443
    
    use_https = input("استفاده از HTTPS؟ (y/n) [y]: ").strip().lower()
    config['https'] = use_https != 'n'
    
    config['username'] = input("نام کاربری ادمین: ").strip()
    config['password'] = input("رمز عبور ادمین: ").strip()
    
    return config

def convert_expiry_time(expiry_time_ms):
    """
    تبدیل تاریخ انقضا از میلی‌ثانیه به ثانیه
    اگر تاریخ گذشته باشد، 1 روز به امروز اضافه می‌کند
    """
    if not expiry_time_ms or expiry_time_ms == 0:
        return 0, "بدون انقضا"
    
    # تبدیل میلی‌ثانیه به ثانیه
    expiry_sec = int(expiry_time_ms / 1000)
    
    # اگر تاریخ انقضا گذشته باشد
    if expiry_sec < time.time():
        # فقط 1 روز به زمان فعلی اضافه کن
        new_expiry = int(time.time() + 1 * 24 * 3600)
        old_date = datetime.fromtimestamp(expiry_sec).strftime('%Y-%m-%d')
        new_date = datetime.fromtimestamp(new_expiry).strftime('%Y-%m-%d')
        return new_expiry, f"تمدید 1 روز (از {old_date} به {new_date})"
    
    return expiry_sec, datetime.fromtimestamp(expiry_sec).strftime('%Y-%m-%d %H:%M:%S')

def calculate_user_volume(total_bytes, up, down):
    """
    محاسبه حجم مناسب برای کاربر
    """
    used_bytes = up + down
    remaining_bytes = total_bytes - used_bytes if total_bytes > 0 else 0
    
    if total_bytes == 0:
        return 0, "نامحدود", "unlimited"
    elif remaining_bytes > 0:
        return remaining_bytes, f"{(remaining_bytes / (1024**3)):.2f} GB", "limited"
    else:
        return 1 * 1024 * 1024 * 1024, "1 GB (شارژ مجدد)", "exhausted"

def extract_users_from_db():
    """استخراج کاربران از دیتابیس X-UI با حجم و تاریخ انقضا"""
    print("\n📡 در حال استخراج اطلاعات از دیتابیس...")
    
    db_path = find_xui_db()
    if not db_path:
        print("❌ فایل دیتابیس پیدا نشد!")
        return []
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # روش اول: استخراج از تیبل client_traffics (اطلاعات کامل)
    try:
        cursor.execute("""
            SELECT ct.email, ct.up, ct.down, ct.total, ct.expiry_time,
                   c.uuid, c.enable, c.limit_ip, c.flow
            FROM client_traffics ct
            LEFT JOIN clients c ON ct.email = c.email
            WHERE ct.enable = 1
        """)
        users_data = cursor.fetchall()
    except:
        # روش دوم: استخراج از تیبل inbounds (روش جایگزین)
        cursor.execute("""
            SELECT c.email, c.uuid, c.total_gb, c.expiry_time, c.enable,
                   c.limit_ip, c.flow, 0 as up, 0 as down
            FROM clients c
            WHERE c.enable = 1
        """)
        users_data = cursor.fetchall()
    
    conn.close()
    
    users = []
    expired_count = 0
    renewed_count = 0
    
    for row in users_data:
        if len(row) >= 9:
            email, up, down, total_bytes, expiry_ms, uuid, enable, limit_ip, flow = row
        elif len(row) >= 8:
            email, uuid, total_gb, expiry_ms, enable, limit_ip, flow, up, down = row
            total_bytes = total_gb * 1024 * 1024 * 1024 if total_gb > 0 else 0
        else:
            continue
        
        if not email or not uuid:
            continue
        
        # محاسبه حجم
        data_limit, volume_desc, volume_status = calculate_user_volume(total_bytes or 0, up or 0, down or 0)
        
        # تبدیل تاریخ انقضا
        expiry_sec, expiry_desc = convert_expiry_time(expiry_ms or 0)
        
        if "تمدید" in expiry_desc:
            renewed_count += 1
        elif expiry_sec > 0:
            expired_count += 1
        
        users.append({
            'email': email,
            'uuid': uuid,
            'data_limit': data_limit,
            'volume_desc': volume_desc,
            'volume_status': volume_status,
            'expiry_time': expiry_sec,
            'expiry_desc': expiry_desc,
            'limit_ip': limit_ip or 0,
            'flow': flow or '',
            'total_gb': (total_bytes / (1024**3)) if total_bytes > 0 else 0,
            'used_gb': ((up or 0) + (down or 0)) / (1024**3)
        })
    
    print(f"   ✅ کاربران استخراج شده: {len(users)}")
    print(f"   📅 کاربران با تاریخ انقضا: {expired_count}")
    if renewed_count > 0:
        print(f"   🔄 کاربران با تمدید 1 روز: {renewed_count}")
    
    return users

def get_marzban_inbounds(token, marzban):
    """دریافت لیست اینباندهای مرزبان"""
    protocol = "https" if marzban['https'] else "http"
    url = f"{protocol}://{marzban['domain']}:{marzban['port']}/api/inbounds"
    headers = {"Authorization": f"Bearer {token}", "accept": "application/json"}
    
    try:
        response = requests.get(url, headers=headers, verify=False, timeout=30)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"❌ خطا در دریافت اینباندها: {e}")
        return None

def create_user_in_marzban(token, user, selected_inbounds, marzban):
    """ایجاد کاربر در مرزبان با حجم و تاریخ انقضا"""
    protocol = "https" if marzban['https'] else "http"
    url = f"{protocol}://{marzban['domain']}:{marzban['port']}/api/user"
    
    data = {
        "username": user['email'],
        "proxies": {
            "vless": {
                "id": user['uuid'],
                "flow": "xtls-rprx-vision"
            }
        },
        "inbounds": selected_inbounds,
        "expire": user['expiry_time'],
        "data_limit": user['data_limit'],
        "data_limit_reset_strategy": "no_reset",
        "status": "active"
    }
    
    headers = {
        "Authorization": f"Bearer {token}",
        "accept": "application/json",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=data, headers=headers, verify=False, timeout=30)
        
        if response.status_code == 200:
            expiry_info = f" | {user['expiry_desc']}" if user['expiry_time'] > 0 else ""
            print(f"   ✅ {user['email']} | {user['volume_desc']}{expiry_info}")
            return True
        elif response.status_code == 409:
            new_username = f"{user['email']}_{int(time.time())%10000}"
            data["username"] = new_username
            response = requests.post(url, json=data, headers=headers, verify=False)
            if response.status_code == 200:
                expiry_info = f" | {user['expiry_desc']}" if user['expiry_time'] > 0 else ""
                print(f"   ✅ {user['email']} -> {new_username} | {user['volume_desc']}{expiry_info}")
                return True
            else:
                print(f"   ❌ {user['email']} - تکراری")
                return False
        else:
            print(f"   ❌ {user['email']} - خطا {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ {user['email']} - خطا: {str(e)[:50]}")
        return False

def show_statistics(users):
    """نمایش آمار کاربران"""
    print("\n" + "="*60)
    print("📊 خلاصه کاربران برای انتقال")
    print("="*60)
    
    active = len(users)
    unlimited = len([u for u in users if u['volume_status'] == 'unlimited'])
    limited = len([u for u in users if u['volume_status'] == 'limited'])
    exhausted = len([u for u in users if u['volume_status'] == 'exhausted'])
    with_expiry = len([u for u in users if u['expiry_time'] > 0])
    renewed = len([u for u in users if "تمدید" in u['expiry_desc']])
    
    print(f"   ✅ کاربران فعال: {active}")
    print(f"   ♾️  کاربران نامحدود: {unlimited}")
    print(f"   📦 کاربران با حجم باقیمانده: {limited}")
    print(f"   🔄 کاربران با حجم تمام شده: {exhausted}")
    print(f"   📅 کاربران با تاریخ انقضا: {with_expiry}")
    if renewed > 0:
        print(f"   🔄 کاربران با تمدید 1 روز: {renewed}")
    
    # نمایش نمونه کاربران با تاریخ انقضا
    users_with_expiry = [u for u in users if u['expiry_time'] > 0]
    if users_with_expiry:
        print("\n📋 نمونه کاربران با تاریخ انقضا:")
        for user in users_with_expiry[:5]:
            print(f"   - {user['email']}: {user['expiry_desc']} | حجم: {user['volume_desc']}")
    
    return active, unlimited, limited, exhausted, with_expiry

def main():
    print("="*60)
    print("🚀 X-UI to Marzban Migration Script")
    print("   انتقال کاربران با حجم باقیمانده و تاریخ انقضا")
    print("="*60)
    
    # استخراج کاربران
    users = extract_users_from_db()
    
    if not users:
        print("❌ هیچ کاربر فعالی یافت نشد!")
        return
    
    # نمایش آمار
    show_statistics(users)
    
    # گرفتن اطلاعات مرزبان
    marzban = get_marzban_config()
    
    # اتصال به مرزبان
    print("\n🔐 در حال اتصال به مرزبان...")
    protocol = "https" if marzban['https'] else "http"
    login_url = f"{protocol}://{marzban['domain']}:{marzban['port']}/api/admin/token"
    
    try:
        response = requests.post(login_url, 
                                data={'username': marzban['username'], 
                                      'password': marzban['password']},
                                verify=False, timeout=30)
        if response.status_code != 200:
            print(f"❌ خطا در اتصال به مرزبان: {response.status_code}")
            return
        token = response.json().get('access_token')
        print("✅ اتصال به مرزبان موفقیت‌آمیز بود")
    except Exception as e:
        print(f"❌ خطا در اتصال به مرزبان: {e}")
        return
    
    # دریافت اینباندها
    print("\n📡 دریافت اینباندهای مرزبان...")
    inbounds = get_marzban_inbounds(token, marzban)
    
    if not inbounds:
        print("❌ دریافت اینباندها ناموفق!")
        return
    
    selected_inbounds = {}
    for protocol_type, items in inbounds.items():
        if items and protocol_type == 'vless':
            selected_inbounds['vless'] = [item.get('tag') for item in items]
    
    if not selected_inbounds:
        print("❌ اینباند VLESS در مرزبان یافت نشد!")
        return
    
    print(f"✅ اینباندهای VLESS: {', '.join(selected_inbounds['vless'])}")
    
    # تأیید نهایی
    print(f"\n⚠️ {len(users)} کاربر به مرزبان منتقل خواهند شد.")
    print("   - حجم باقیمانده هر کاربر حفظ می‌شود")
    print("   - تاریخ انقضا هر کاربر منتقل می‌شود")
    print("   - تاریخ‌های گذشته فقط 1 روز تمدید می‌شوند")
    
    confirm = input("\nآیا ادامه می‌دهید؟ (y/n): ").strip().lower()
    if confirm != 'y':
        print("❌ عملیات لغو شد.")
        return
    
    # شروع انتقال
    print("\n" + "="*60)
    print("🚀 در حال انتقال کاربران...")
    print("="*60)
    
    success = 0
    fail = 0
    
    for i, user in enumerate(users, 1):
        print(f"[{i}/{len(users)}] ", end="")
        if create_user_in_marzban(token, user, selected_inbounds, marzban):
            success += 1
        else:
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
        print("   ✨ تاریخ انقضا و حجم باقیمانده کاربران حفظ شده است.")
        renewed_count = len([u for u in users if "تمدید" in u['expiry_desc']])
        if renewed_count > 0:
            print(f"   🔄 {renewed_count} کاربر با تاریخ گذشته، 1 روز تمدید شدند.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ عملیات توسط کاربر متوقف شد.")
    except Exception as e:
        print(f"\n❌ خطای غیرمنتظره: {e}")
