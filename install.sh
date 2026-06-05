#!/bin/bash

# اسکریپت نصب و اجرا برای انتقال X-UI به مرزبان

echo "🚀 در حال آماده‌سازی اسکریپت انتقال X-UI به مرزبان..."
echo "======================================================"

# آدرس فایل اصلی اسکریپت پایتون شما در گیت‌هاب
# دقت کنید که نام فایل اصلی باید migrate.py باشد
SCRIPT_URL="https://raw.githubusercontent.com/JavadWolf-af/X-ui-To-Marzban/main/migrate.py"

# دانلود و اجرای اسکریپت پایتون
curl -sSL "$SCRIPT_URL" -o /tmp/migrate.py && python3 /tmp/migrate.py

# پاک کردن فایل موقت پس از اجرا
rm -f /tmp/migrate.py

echo ""
echo "✅ اجرای اسکریپت به پایان رسید."
