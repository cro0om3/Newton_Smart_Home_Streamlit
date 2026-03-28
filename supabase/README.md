# Supabase – Newton Smart Home

## تم تشغيل الهجرة

تم تطبيق الملف `migrations/20250207120000_newton_smart_home_full_schema.sql` على قاعدة Supabase (الجداول، RLS، الفهارس، والـ seed التلقائي).

## إعادة تشغيل الهجرة لاحقاً

```bash
# ضع سلسلة الاتصال في أحد الخيارات:
# - متغير البيئة: DB_CONNECTION_STRING أو SUPABASE_DB_URL
# - ملف: data/supabase_db_url.txt (سطر واحد)
# - ملف: .env (سطر DB_CONNECTION_STRING=...)

python scripts/run_supabase_migration.py
```

ملف `data/supabase_db_url.txt` مُضاف إلى `.gitignore` ولا يُرفع إلى Git.
