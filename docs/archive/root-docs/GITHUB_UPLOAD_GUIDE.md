# 🚀 دليل رفع المشروع على GitHub
## Complete Guide to Upload Project on GitHub

---

## 📋 متطلبات مسبقة
- ✅ Git مثبت على النظام
- ✅ حساب GitHub نشط
- ✅ توكن وصول شخصي (Personal Access Token) أو مفتاح SSH

---

## 🎯 الخطوات السريعة (5 دقائق)

### الخطوة 1: إنشاء Repository على GitHub

1. اذهب إلى https://github.com/new
2. **ملء البيانات:**
   - **Repository name:** `NUZUM`
   - **Description:** نظام إدارة الحضور والانصراف - Smart Attendance Tracking System
   - **Public / Private:** اختر حسب احتياجك
   - **Initialize:** اختر **Do not initialize** (سنفعل ذلك محلياً)

3. اضغط **Create repository**

### الخطوة 2: تشغيل السكريبت

#### 🪟 Windows - PowerShell:
```powershell
cd D:\nuzm
.\SETUP_GITHUB.ps1
```

#### 🐧 Linux / macOS:
```bash
cd ~/nuzm  # أو مسار المشروع
bash SETUP_GITHUB.sh  # (سيتم إنشاؤه)
```

### الخطوة 3: ربط مع GitHub

بعد تشغيل السكريبت، قم بتنفيذ:

#### اختيار: HTTPS (أسهل - موصى به للمبتدئين)
```bash
git remote add origin https://github.com/YOUR_USERNAME/NUZUM.git
git branch -M main
git push -u origin main
```

#### اختيار: SSH (أكثر أماناً - موصى به للمحترفين)
```bash
git remote add origin git@github.com:YOUR_USERNAME/NUZUM.git
git branch -M main
git push -u origin main
```

⚠️ **تحذير:** استبدل `YOUR_USERNAME` باسم حسابك على GitHub

### الخطوة 4: أدخل بيانات المصادقة

- **HTTPS:** اختر Personal Access Token (PAT)
- **SSH:** استخدم مفتاحك الخاص

---

## 📝 الخطوات التفصيلية

### 1️⃣ تثبيت Git

#### Windows:
```powershell
# باستخدام Chocolatey
choco install git

# أو تحميل من
# https://git-scm.com/download/win
```

#### Linux (Ubuntu/Debian):
```bash
sudo apt update
sudo apt install git
```

#### macOS:
```bash
brew install git
```

**تحقق:**
```bash
git --version
```

### 2️⃣ إعداد Git المحلي

```bash
# الاسم
git config --global user.name "Your Name"

# البريد الإلكتروني
git config --global user.email "your.email@example.com"

# تحقق
git config --global --list
```

### 3️⃣ إنشاء Personal Access Token (HTTPS)

للطريقة الآمنة مع HTTPS:

1. اذهب إلى: https://github.com/settings/tokens
2. اضغط **Generate new token**
3. **ملء البيانات:**
   - **Token name:** `NUZUM-Upload`
   - **Expiration:** 90 days
   - **Scopes:** اختر ✅ `repo`
4. اضغط **Generate token**
5. **انسخ التوكن** (لن تراه مرة أخرى!)

### 4️⃣ إعداد SSH (اختياري - أكثر أماناً)

```bash
# توليد مفتاح
ssh-keygen -t ed25519 -C "your.email@github.com"

# اترك كل شيء بالافتراضي واضغط Enter

# انسخ المفتاح العام
# Windows PowerShell:
Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub | Set-Clipboard

# Linux/macOS:
cat ~/.ssh/id_ed25519.pub | pbcopy

# أضفه إلى GitHub: https://github.com/settings/keys
```

### 5️⃣ إنشاء Repository المحلي

```bash
cd D:\nuzm  # مسار المشروع

# تهيئة (إن لم يكن Git موجوداً)
git init

# إضافة كل الملفات
git add .

# عمل commit
git commit -m "Initial commit: NUZUM System v1.0 - Production Ready"

# تعيين فرع رئيسي
git branch -M main
```

### 6️⃣ ربط مع GitHub

#### اختيار HTTPS (للبدء السريع):
```bash
git remote add origin https://github.com/YOUR_USERNAME/NUZUM.git
git push -u origin main
```

عند الطلب، أدخل:
- **Username:** اسم حسابك على GitHub
- **Password:** استخدم الـ Personal Access Token (ليس كلمة السر)

#### اختيار SSH (للأمان الأعلى):
```bash
git remote add origin git@github.com:YOUR_USERNAME/NUZUM.git
git push -u origin main
```

---

## ✅ التحقق من النجاح

```bash
# تحقق من الـ remote
git remote -v

# يجب أن تري:
# origin  https://github.com/YOUR_USERNAME/NUZUM.git (fetch)
# origin  https://github.com/YOUR_USERNAME/NUZUM.git (push)

# تحقق من السجل
git log --oneline

# تحقق من الفرع
git branch -a
```

---

## 🔄 الدفع والسحب الدوري

### بعد إجراء تغييرات محلية:

```bash
# 1. تحقق من التغييرات
git status

# 2. أضف الملفات المعدّلة
git add .

# 3. عمل commit
git commit -m "وصف التغييرات | Description of changes"

# 4. دفع التغييرات
git push origin main
```

### سحب التحديثات من الخادم البعيد:

```bash
git pull origin main
```

---

## 🆘 استكشاف الأخطاء الشائعة

### ❌ الخطأ: `fatal: remote origin already exists`

```bash
# الحل:
git remote remove origin
git remote add origin https://github.com/YOUR_USERNAME/NUZUM.git
```

### ❌ الخطأ: `error: src refspec main does not match any`

```bash
# الحل:
git commit -m "First commit"
git branch -M main
git push -u origin main
```

### ❌ الخطأ: `fatal: Authentication failed`

```bash
# للـ HTTPS:
# - تأكد من استخدام Personal Access Token (ليس كلمة السر)
# - امسح بيانات المصادقة المحفوظة

# Windows:
# اذهب إلى: 
# Settings > Credential Manager > Windows Credentials
# احذف github.com entries

# Linux:
git credential-cache exit

# محاولة جديدة:
git push origin main
```

### ❌ الخطأ: `error: Please commit your changes before you merge`

```bash
# حل 1: عمل commit
git add .
git commit -m "Save changes"

# حل 2: تجاهل التغييرات (خطر!)
git stash
git pull origin main
git stash pop
```

---

## 📊 حالة المشروع بعد الرفع

```
✅ Repository محرّر على GitHub
✅ جميع الملفات مرفوعة (50+ files)
✅ السجل الكامل (git history) متاح
✅ README محترف
✅ LICENSE جاهز
✅ Configuration واضح (.gitignore)
```

---

## 🎓 ممارسات أفضلة

### ✅ افعل:
```bash
# اكتب رسائل commit واضحة
git commit -m "Fix: logout redirect to login page"
git commit -m "Feature: add health check system"
git commit -m "Docs: update README with examples"

# استخدم فروع للميزات الجديدة
git checkout -b feature/new-feature
git commit -m "Add new feature"
git push origin feature/new-feature
# (ثم اعمل Pull Request على GitHub)
```

### ❌ لا تفعل:
```bash
# ❌ رسائل غامضة
git commit -m "fix"
git commit -m "update"

# ❌ رفع البيانات الحساسة
# لا تضع: كلمات السر، توكنات، مفاتيح API

# ❌ تغيير السجل بعد الدفع
git reset --hard HEAD~1
git push --force  # خطير جداً!
```

---

## 📚 موارد إضافية

- **توثيق Git:** https://git-scm.com/doc
- **GitHub Help:** https://docs.github.com
- **GitHub Desktop:** https://desktop.github.com/
- **GitKraken (GUI):** https://www.gitkraken.com/

---

## 🎉 تم بنجاح!

مشروعك الآن على GitHub! 

### الخطوات التالية:
1. ✅ شارك الرابط مع الفريق
2. ✅ أضف Contributors
3. ✅ أعدّ CI/CD (اختياري)
4. ✅ استمر في التطوير

---

**آخر تحديث:** 22 فبراير 2026  
**الإصدار:** 1.0  
**الحالة:** ✅ جاهز للرفع على GitHub
