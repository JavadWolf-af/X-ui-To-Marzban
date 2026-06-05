# 🔄 X-UI to Marzban Migration Script

### <div dir="rtl">انتقال خودکار کاربران از X-UI به Marzban</div>

![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Python](https://img.shields.io/badge/python-3.6+-yellow.svg)

---

## ✨ Features / ویژگی‌ها

<div dir="ltr">

* 🚀 Fast one-command execution
* 🤖 Automatic X-UI database detection
* 📊 Accurate remaining traffic calculation
* 🔐 Full VLESS support
* 🛡️ Secure migration with validation
* 📝 Detailed success/failure reports

</div>

---

## 🎯 <div dir="rtl">منطق انتقال کاربران</div>

| وضعیت کاربر | حجم باقی‌مانده | نتیجه انتقال |
|--------------|----------------|---------------|
| ✅ فعال و نامحدود | ∞ | نامحدود |
| ✅ فعال با حجم باقی‌مانده | بیشتر از 0 | همان حجم باقی‌مانده |
| ✅ فعال با حجم تمام‌شده | 0 GB | 1 GB |
| ❌ غیرفعال | - | منتقل نمی‌شود |

---

## 📋 <div dir="rtl">پیش‌نیازها</div>

<div dir="rtl">

* Ubuntu / Debian
* Root access
* X-UI installed
* Marzban installed
* Internet connection

</div>

---

## 🚀 Installation

```bash
bash <(curl -Ls https://raw.githubusercontent.com/JavadWolf-af/X-ui-To-Marzban/main/install.sh)
```

---

## 🖥️ <div dir="rtl">نمونه اجرا</div>

```text
🚀 X-UI to Marzban Migration Script

✅ دیتابیس پیدا شد: x-ui.db

🔐 تنظیمات پنل مرزبان
...
```

---

## 📈 <div dir="rtl">گزارش انتقال</div>

<div dir="rtl">

- تعداد کاربران منتقل‌شده
- تعداد کاربران ناموفق
- حجم باقی‌مانده
- خطاها

</div>

---

## 🛠️ Troubleshooting / عیب‌یابی

| Problem (EN) | راه‌حل (FA) |
|--------------|-------------|
| DB not found | فایل x-ui.db را قرار دهید |
| Connection error | تنظیمات پنل را بررسی کنید |
| VLESS missing | اینباند بسازید |

---

## ❤️ Support

<div align="center">

### 💎 TON Wallet

```
UQA1qH3125AdKwyksxBmcqYVcB4z-WZZwbYPxlyLJWOjKgGH
```

⭐ Star دادن به پروژه بهترین حمایت است

</div>
