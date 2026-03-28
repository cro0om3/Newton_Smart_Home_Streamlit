# توثيق مشروع Newton Smart Home - Quotation App

## مقدمة
- تطبيق مبني على Streamlit لتوليد عروض أسعار وفواتير وإيصالات بنمط صفحة واحدة عبر `st.session_state.active_page` بدل الصفحات المتعددة.
- يعتمد على ملفات Excel للتخزين وقوالب Word للتصدير؛ لا توجد قاعدة بيانات خلفية.
- واجهة مستوحاة من أسلوب Apple مع ثيم ضوء/ظلام و CSS مضمن.

## طريقة التشغيل السريع
- تثبيت المتطلبات: `pip install -r requirements.txt`
- تشغيل محلي: `streamlit run main.py` (المنفذ الافتراضي 8501)
- تشغيل على منفذ مخصص: `streamlit run main.py --server.port 8502`
- Python 3.10+ موصى به. حزمة `pdfkit` تراثية وغير مستخدمة حالياً.

## هيكل المشروع (مسارات مهمة)
- `main.py`: نقطة الدخول، الثيم، الملاحة (أزرار علوية + شريط جانبي)، التحقق بالـ PIN، وتوجيه الصفحات.
- `pages_custom/` صفحات التطبيق:
  - `quotation_page.py`: إنشاء عروض الأسعار، إضافة منتجات، توليد Word/PDF، تحديث العملاء والسجلات.
  - `invoice_page.py`: إنشاء الفواتير من عرض سابق أو جديدة، توليد Word، تحديث السجلات وربط base_id.
  - `receipt_page.py`: إصدار إيصالات مبنية على الفواتير.
  - `dashboard_page.py`: لوحات ومؤشرات.
  - `customers_page.py`: إدارة العملاء.
  - `products_page.py`: إدارة الكتالوج (Excel) مع دعم صورة المنتج Base64.
  - `reports_page.py`: تقارير.
  - `settings_page.py`: تعديل الإعدادات في `data/settings.json`.
- `utils/`:
  - `auth.py`: users.xlsx، التحقق من PIN، الأدوار والصلاحيات.
  - `logger.py`: تسجيل الأحداث في logs.xlsx.
  - `settings.py`: تحميل/حفظ الإعدادات الافتراضية.
- `data/`:
  - بيانات التشغيل: `products.xlsx`, `records.xlsx`, `customers.xlsx`, `users.xlsx`, `logs.xlsx` (تُنشأ تلقائياً).
  - الإعدادات: `settings.json`.
  - قوالب Word: `quotation_template.docx`, `invoice_template.docx`, `receipt_template.docx`.
  - الشعارات: `data/newton_logo.(png|svg)` ثم `data/logo.(png|svg)`.
  - مجلد exports يُنشأ عند حفظ ملفات مصدّرة محلياً.

## تدفق الحالة والملاحة
- المتغير `st.session_state.active_page` يحدد الصفحة الحالية. تغيير الصفحة يتم بالأزرار ثم `st.rerun()`.
- جداول البنود لكل صفحة داخل الـ session (مثلاً `product_table`, `invoice_table`) ولا تُشارك بين الصفحات؛ أعد التهيئة إذا أردت البدء من جديد.
- الثيم يُحدد في `st.session_state.ui_theme` (light/dark) و CSS في `main.py`.

## المصادقة والصلاحيات
- تسجيل الدخول برمز PIN من `data/users.xlsx`. رموز افتراضية: Admin=1234، Staff=5678، Viewer=9999.
- دوال أساسية: `validate_pin()`, `can_access_page()`, `is_admin()` في `utils/auth.py`.
- كل صفحة تتحقق من الإذن؛ الأحداث تُسجّل عبر `log_event()` إلى `data/logs.xlsx`.

## تخزين البيانات (Excel)
- `data/products.xlsx`: أعمدة مطلوبة `Device`, `Description`, `UnitPrice`, `Warranty`; عمود اختياري `ImageBase64` لصور المنتجات.
- `data/records.xlsx`: سجل كل المعاملات (`base_id`, `date`, `type` = q/i/r, `number`, `amount`, `client_name`, `phone`, `location`, `note`). الربط بين عرض/فاتورة/إيصال يتم عبر `base_id`.
- `data/customers.xlsx`: يُنشأ ويُحدّث آلياً من العروض والفواتير (الاسم، الهاتف، الموقع، البريد، الحالة، الملاحظات، الوسوم، المتابعة، المكلّف، آخر نشاط).
- `data/users.xlsx`: المستخدمون و PIN والصلاحيات.
- `data/logs.xlsx`: سجل الأحداث.
- الملفات تُنشأ تلقائياً عند غيابها، والأعمدة تُوحّد بالأحرف الصغيرة عند التحميل.

## قوالب Word وآلية التوليد
- القوالب في `data/<type>_template.docx` وتستخدم المتغيّرات `{{placeholder}}` لاستبدال النص داخل كل خلايا الجداول.
- جدول المنتجات يُكتشف بوجود خلية أولى تحتوي على "item no" (غير حساس لحالة الأحرف). صف يحمل "last" يحدد نهاية التكرار، والصفوف الزائدة تُحذف.
- الأعمدة المستخدمة لملء البنود: `Item No`, `Product / Device`, `Description`, `Qty`, `Unit Price (AED)`, `Line Total (AED)`, `Warranty (Years)`.
- أهم placeholders:
  - العروض: `{{client_name}}`, `{{quote_no}}`, `{{client_location}}`, `{{client_phone}}`, `{{prepared_by}}`, `{{approved_by}}`, `{{total1}}`, `{{installation_cost}}`, `{{Price}}`, `{{Total}}`, مع تخفيضات اختيارية `{{discount_value}}`, `{{discount_percent}}`, `{{total_discount}}`, `{{grand_total}}`.
  - الفواتير: `{{client_name}}`, `{{invoice_no}}`, `{{client_location}}`, `{{client_phone}}`, `{{total_products}}`, `{{installation}}`, `{{discount_value}}`, `{{discount_percent}}`, `{{grand_total}}`.
  - الإيصالات مشابهة للفواتير (راجع القالب والصفحة عند الحاجة).
- صور المنتجات: إذا وُجد `ImageBase64` في الكتالوج تُدرج داخل خلية المنتج بأبعاد من الإعدادات (`quote_product_image_width_cm`, `quote_product_image_height_cm`).
- تحويل PDF في صفحة العروض يستخدم ConvertAPI (مفتاح مضمّن في الكود) بكتابة DOCX مؤقت ثم تحويله.

## لمحة عن منطق الصفحات
- **Quotation**: اختيار منتجات من الكتالوج، إضافة إلى `product_table`, حساب الإجماليات (تركيب + خصم)، توليد Word/PDF، حفظ سجل بنوع `q`، وتحديث/إضافة العميل.
- **Invoice**: من عرض سابق أو جديد، نفس منطق الخصومات والتركيب، توليد Word، حفظ سجل بنوع `i` وربط `base_id` بالعرض عند توفره، وتحديث العميل.
- **Receipt**: يبنى على فاتورة محفوظة ويُسجل بنوع `r`.
- **Dashboard/Reports**: قراءة `records.xlsx` و/أو `logs.xlsx` لعرض المؤشرات.
- **Customers/Products**: إدارة الجداول المخزنة في Excel مع واجهات مبسطة.
- **Settings**: تعديل مفاتيح `data/settings.json` (اسم الشركة، المحضّر/المعتمد الافتراضيان، الاتصال، العملة، أبعاد صور المنتج...).

## الثيم والتخصيص
- CSS للثيمات مضمّن في `main.py` ويتحكم بالألوان والخلفيات والحدود والأزرار.
- أزرار الملاحة تتلوّن حسب الصفحة النشطة (CSS يحقن ديناميكياً).
- خط افتراضي: "SF Pro Display" مع سلسلة fallback.

## السجلات والتتبع
- كل دخول/خروج أو فتح صفحة أو إنشاء مستند يُسجَّل في `data/logs.xlsx` عبر `utils/logger.py`.
- يمكن استخدام صفحة التقارير أو اللوحة لعرض ملخصات.

## الإعدادات القابلة للتعديل
- مفاتيح افتراضية في `data/settings.json`: `company_name`, `default_prepared_by`, `default_approved_by`, `contact_email`, `contact_phone`, `currency`, أبعاد صور المنتج للواجهة والقالب.
- يمكن التعديل يدوياً أو عبر `settings_page.py`; الدوال في `utils/settings.py` تكفل إنشاء الملف وملء المفاتيح الناقصة.

## نصائح تشغيل
- تأكد من وجود قوالب Word الثلاثة في مجلد `data/` بأسمائها الصحيحة.
- حافظ على أسماء الأعمدة في ملفات Excel كما هي مذكورة لتفادي أعطال التوليد.
- ملفات البيانات (`*.xlsx`) مُتجاهَلة في Git؛ خذ نسخاً احتياطية عند الحاجة.
- تعطل تحويل PDF غالباً يرتبط بمفتاح ConvertAPI أو الاتصال الشبكي.
