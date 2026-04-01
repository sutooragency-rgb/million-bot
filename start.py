import subprocess
import sys
import time

print("🚀 جاري إقلاع إمبراطورية المليون...")
print("🌐 تشغيل الداشبورد (غرفة القيادة)...")

# تشغيل ملف الداشبورد (تم التعديل ليقرأ dashboard.py)
dashboard_process = subprocess.Popen([sys.executable, "dashboard.py"])

# ننتظر ثانيتين حتى يشتغل الداشبورد براحته
time.sleep(2)

print("🤖 تشغيل محرك البوت...")
# تشغيل ملف البوت
bot_process = subprocess.Popen([sys.executable, "main.py"])

try:
    # إبقاء السكربت شغال وتوحيد الشاشة
    dashboard_process.wait()
    bot_process.wait()
except KeyboardInterrupt:
    print("\n🛑 تم إيقاف النظام بالكامل.")
    dashboard_process.terminate()
    bot_process.terminate()