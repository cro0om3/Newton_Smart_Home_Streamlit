# رفع GitHub + نشر Streamlit Cloud

## 1) ماذا ترفع على GitHub؟

ارفع **محتويات مجلد `1NEWTON` كجذر المستودع** (Root)، بحيث يكون عندك مباشرة:

- `main.py`
- `requirements.txt`
- مجلدات `pages_custom`، `utils`، `templates`، `data` (حسب ما تريد مشاركته)، إلخ.

**لا ترفع أسراراً:** ملف `.streamlit/secrets.toml` مُستثنى في `.gitignore` ولا يُرفع. أي ملف فيه `DB_CONNECTION_STRING` أو مفاتيح API لا يُضاف للمستودع.

### خطوات سريعة (من داخل مجلد `1NEWTON`)

```powershell
git init
git add .
git status
```

راجع `git status` وتأكد أن **`secrets.toml` غير ظاهر** في الملفات المضافة.

```powershell
git commit -m "Newton Smart Home Streamlit app"
git branch -M main
git remote add origin https://github.com/YOUR_USER/YOUR_REPO.git
git push -u origin main
```

إن كان المستودع موجوداً مسبقاً: استخدم `git remote set-url` أو `git pull` ثم `git push` حسب وضعك.

---

## 2) إعداد التطبيق على Streamlit Cloud

1. ادخل [share.streamlit.io](https://share.streamlit.io) وسجّل الدخول بـ GitHub.
2. **New app** → اختر المستودع والفرع `main`.
3. **Main file path:** اكتب `main.py` (إذا كان `main.py` في جذر المستودع كما فوق).
4. **Advanced settings → Python version:** يفضّل **3.11** أو **3.12** (متوافق مع قراءة `secrets.toml` المحلي للسكربتات).

---

## 3) الأسرار (Secrets) — انسخ والصق في واجهة Streamlit

في التطبيق على Streamlit: **App settings → Secrets**.

الصق القالب التالي واستبدل القيم الوهمية بقيمك الحقيقية:

```toml
# إلزامي — اتصال Postgres (Supabase)
DB_CONNECTION_STRING = "postgresql://USER:PASSWORD@HOST:5432/postgres?sslmode=require"

# اختياري — مساعد OpenAI في Power Tools (ويمكن أيضاً حفظ المفتاح من الإعدادات داخل التطبيق)
OPENAI_API_KEY = "sk-..."

# اختياري — تحويل HTML→PDF عبر ConvertAPI إذا WeasyPrint غير متاح في البيئة
CONVERTAPI_SECRET = "..."
```

### ملاحظات

- **`DB_CONNECTION_STRING`:** من Supabase → Project Settings → Database → Connection string (URI)، مع كلمة مرور المستخدم (ليس الـ anon key).
- **`OPENAI_API_KEY` و `CONVERTAPI_SECRET`:** احذف السطر بالكامل أو اترك القيمة فارغة إن لم تستخدم الخدمة.
- بعد حفظ الـ Secrets أعد تشغيل التطبيق (**Reboot app**) من لوحة Streamlit.

---

## 4) قاعدة البيانات والملفات على السحابة

- بيانات التطبيق الرئيسية تُخزَّن في **Supabase** عند استخدام الجداول؛ الملفات تحت `data/` على Streamlit **مؤقتة** وقد تُفقد عند إعادة النشر. خطط للنسخ الاحتياطي أو لاستمرارية البيانات عبر DB.

---

## 5) تحقق سريع بعد النشر

- تسجيل الدخول بالـ PIN.
- إنشاء عرض سعر / فاتورة / إيصال وحفظ HTML.
- التأكد أن الأرشيف يقرأ من قاعدة البيانات كما محلياً.

للاختبار على الجهاز قبل الرفع:

```powershell
pip install -r requirements.txt
streamlit run main.py
```

```powershell
python scripts/e2e_smoke.py
```
