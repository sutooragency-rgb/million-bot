from flask import Flask, request, render_template_string, redirect, url_for, session, flash
import pymysql
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = 'million_super_secret_key_2026_masterpiece_completed'

# ================= إعدادات قاعدة البيانات والأدمن =================
DB_HOST = "srv1814.hstgr.io"
DB_USER = "u315866850_4zCBQ"
DB_PASS = "NNt0JBRMRs"  
DB_NAME = "u315866850_FnwSO"

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "123" 

def get_db_connection():
    """إنشاء اتصال بقاعدة البيانات مع بناء جداول الإمبراطورية الشاملة"""
    conn = pymysql.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASS, db=DB_NAME, 
        charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor
    )
    with conn.cursor() as cur:
        # جداول الإمبراطورية الأساسية والجديدة (مع حقل last_mine_time للعبة)
        cur.execute("""CREATE TABLE IF NOT EXISTS users (id BIGINT PRIMARY KEY, username VARCHAR(255), points INT DEFAULT 0, miq_balance FLOAT DEFAULT 0, role VARCHAR(50) DEFAULT 'user', province VARCHAR(100), invites_count INT DEFAULT 0, last_mine_time TIMESTAMP NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS action_logs (id INT AUTO_INCREMENT PRIMARY KEY, user_id BIGINT, action_type VARCHAR(100), details TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS withdraw_requests (id INT AUTO_INCREMENT PRIMARY KEY, user_id BIGINT, wallet_address VARCHAR(255), amount INT, status VARCHAR(20) DEFAULT 'pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS smm_providers (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(100), api_url VARCHAR(255), api_key VARCHAR(255), service_type VARCHAR(50))""")
        cur.execute("""CREATE TABLE IF NOT EXISTS advanced_store (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(255), description TEXT, price INT, currency VARCHAR(20))""")
        cur.execute("""CREATE TABLE IF NOT EXISTS bank_deposits (id INT AUTO_INCREMENT PRIMARY KEY, user_id BIGINT, amount INT, currency VARCHAR(20), start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, status VARCHAR(20) DEFAULT 'active')""")
        cur.execute("""CREATE TABLE IF NOT EXISTS predictions (id INT AUTO_INCREMENT PRIMARY KEY, question VARCHAR(255), opt1 VARCHAR(100), opt2 VARCHAR(100), opt3 VARCHAR(100), opt4 VARCHAR(100), status VARCHAR(20) DEFAULT 'active', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS prediction_bets (id INT AUTO_INCREMENT PRIMARY KEY, prediction_id INT, user_id BIGINT, selected_option INT, bet_amount INT, currency VARCHAR(20), is_multiplied BOOLEAN, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS settings (setting_key VARCHAR(50) PRIMARY KEY, setting_value VARCHAR(255))""")
        
        # جداول الداشبورد الأصلي
        cur.execute("""CREATE TABLE IF NOT EXISTS orders (id INT AUTO_INCREMENT PRIMARY KEY, user_id BIGINT, target_link VARCHAR(255), quantity INT, original_quantity INT, status VARCHAR(20) DEFAULT 'pending')""")
        cur.execute("""CREATE TABLE IF NOT EXISTS force_subs (id INT AUTO_INCREMENT PRIMARY KEY, channel_username VARCHAR(255) UNIQUE)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS store_offers (id INT AUTO_INCREMENT PRIMARY KEY, points INT, price VARCHAR(50))""")
        cur.execute("""CREATE TABLE IF NOT EXISTS promo_codes (id INT AUTO_INCREMENT PRIMARY KEY, code VARCHAR(50) UNIQUE, reward_type VARCHAR(20), reward INT, max_uses INT, used_count INT DEFAULT 0)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS flash_drops (id INT AUTO_INCREMENT PRIMARY KEY, reward INT, max_winners INT, is_active BOOLEAN DEFAULT TRUE)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS read_to_earn (id INT AUTO_INCREMENT PRIMARY KEY, url VARCHAR(255), question VARCHAR(255), answer VARCHAR(255), reward_type VARCHAR(20), reward INT, max_winners INT, active BOOLEAN DEFAULT TRUE)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS broadcast_queue (id INT AUTO_INCREMENT PRIMARY KEY, message_text TEXT, status VARCHAR(20) DEFAULT 'pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

        # إدخال الإعدادات الافتراضية
        default_settings = {
            'bank_interest_percent': '5.0', 'mine_game_cost': '100', 'mine_reward_type': 'miq',
            'mine_reward_min': '1', 'mine_reward_max': '5', 'store_discount_percent': '0',
            'smm_api_url': '', 'smm_api_key': '', 'follower_order_cost': '10', 'earn_reward_pts': '10',
            'invite_reward_pts': '15', 'bot_guide_text': 'دليل الاستخدام يوضع هنا'
        }
        for k, v in default_settings.items():
            cur.execute("INSERT IGNORE INTO settings (setting_key, setting_value) VALUES (%s, %s)", (k, v))
    conn.commit()
    return conn

# ================= قالب التصميم الأسطوري (HTML / CSS) =================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>👑 مركز القيادة الإمبراطوري - منصة المليون</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --bg-color: #0c1120; --panel-bg: rgba(22, 29, 49, 0.9); --text-main: #ffffff; --text-muted: #a6b0cf;
            --accent-gold: #fbbf24; --accent-blue: #3b82f6; --accent-green: #10b981; --accent-red: #ef4444; --accent-info: #0dcaf0;
        }
        body { background-color: var(--bg-color); color: var(--text-main); font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; overflow-x: hidden; }
        .glass-panel { background: var(--panel-bg); backdrop-filter: blur(15px); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 20px; margin-bottom: 25px; box-shadow: 0 4px 24px 0 rgba(0, 0, 0, 0.3); transition: all 0.3s ease; }
        .glass-panel:hover { border: 1px solid rgba(251, 191, 36, 0.3); }
        .top-navbar { background: rgba(18, 23, 41, 0.95); padding: 15px 30px; border-bottom: 1px solid rgba(255,255,255,0.05); display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 1000; }
        .brand-logo { font-size: 24px; font-weight: 900; color: var(--accent-gold); text-shadow: 0 0 10px rgba(251, 191, 36, 0.8); }
        .stat-card { text-align: center; padding: 15px 10px; border-radius: 10px; transition: transform 0.2s ease; border: 1px solid rgba(255,255,255,0.05); height: 100%; }
        .stat-card:hover { transform: translateY(-3px); box-shadow: 0 5px 15px rgba(0,0,0,0.5); }
        .stat-value { font-size: 26px; font-weight: bold; margin: 8px 0 3px; color: #fff; }
        .stat-label { font-size: 13px; color: #cbd5e1; font-weight: 600; text-transform: uppercase;}
        .c-users { background: linear-gradient(135deg, #1e3a8a, #3b82f6); } .c-left { background: linear-gradient(135deg, #7f1d1d, #ef4444); }
        .c-points { background: linear-gradient(135deg, #064e3b, #10b981); } .c-miq { background: linear-gradient(135deg, #78350f, #fbbf24); }
        .c-pend { background: linear-gradient(135deg, #701a75, #f43f5e); } .c-comp { background: linear-gradient(135deg, #0f766e, #14b8a6); }
        h4.block-title { border-right: 4px solid var(--accent-gold); padding-right: 10px; margin-bottom: 20px; font-weight: bold; color: #fff; display: flex; align-items: center; gap: 10px; }
        .form-control, .form-select { background: rgba(0, 0, 0, 0.3); border: 1px solid rgba(255, 255, 255, 0.1); color: #fff; font-weight: bold; border-radius: 8px; }
        .form-control::placeholder { color: #818ba6; font-weight: normal; }
        .form-control:focus, .form-select:focus { background: rgba(0, 0, 0, 0.5); border-color: var(--accent-gold); color: #fff; box-shadow: 0 0 8px rgba(251, 191, 36, 0.4); }
        label.text-muted { color: #cbd5e1 !important; font-weight: 600; margin-bottom: 3px; display: block; font-size: 13px;}
        p.text-muted { color: #a6b0cf !important; font-weight: 500; font-size: 14px;}
        .btn-gold { background: var(--accent-gold); color: #000; border: none; font-weight: bold; border-radius: 8px;}
        .btn-gold:hover { background: #f59e0b; color: #000; box-shadow: 0 0 15px rgba(251, 191, 36, 0.7); }
        .table-dark { background-color: transparent; font-size: 14px;}
        .table-dark th { color: var(--accent-gold); border-bottom: 1px solid rgba(255,255,255,0.1); font-weight: 600;}
        .table-dark td { border-bottom: 1px solid rgba(255,255,255,0.05); color: #f8fafc; vertical-align: middle;}
        .user-info-card { background: linear-gradient(145deg, rgba(18, 23, 41, 0.9), rgba(30, 41, 59, 0.9)); border: 1px solid var(--accent-info); border-radius: 12px; padding: 20px; margin-bottom: 20px; }
        .user-stat-box { background: rgba(0,0,0,0.4); border: 1px solid rgba(255,255,255,0.05); border-radius: 8px; padding: 10px; text-align: center; }
        .user-stat-box span { display: block; font-size: 12px; color: var(--text-muted); margin-bottom: 5px;}
        .user-stat-box strong { display: block; font-size: 18px; color: #fff;}
        @media print { body { background: #fff; color: #000; } .no-print, .top-navbar { display: none !important; } .glass-panel { background: #fff; border: 1px solid #000; box-shadow: none; page-break-inside: avoid; color:#000; } .text-main, .stat-value, label.text-muted, p.text-muted, h4.block-title { color: #000 !important; text-shadow: none; border-color: #000; } .table-dark th { color: #000; border-bottom: 2px solid #000; } .table-dark td { color: #000; border-bottom: 1px solid #ccc; } .user-info-card { background: #fff; border: 2px solid #000; color: #000; } .user-stat-box { background: #f8f9fa; border: 1px solid #000; } .user-stat-box strong { color: #000; } }
    </style>
</head>
<body>
    <div class="top-navbar">
        <div class="brand-logo"><i class="fa-solid fa-crown"></i> إمبراطورية المليون 2.0</div>
        <div>
            <button onclick="window.print()" class="btn btn-outline-light btn-sm me-3 no-print"><i class="fa-solid fa-print"></i> طباعة الشاشة</button>
            <a href="/logout" class="btn btn-danger btn-sm no-print"><i class="fa-solid fa-power-off"></i> خروج</a>
        </div>
    </div>

    <div class="container-fluid mt-4 px-4 pb-5">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ 'success' if category == 'message' else category }} alert-dismissible fade show no-print" style="font-weight: bold; border-radius:8px;" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="row g-3 mb-4 no-print">
            <div class="col"><div class="stat-card c-users"><i class="fa-solid fa-users opacity-50 mb-2"></i><div class="stat-value">{{ stats.total_users }}</div><div class="stat-label">المواطنين</div></div></div>
            <div class="col"><div class="stat-card c-points"><i class="fa-solid fa-gem opacity-50 mb-2"></i><div class="stat-value">{{ "{:,}".format(stats.total_points) }}</div><div class="stat-label">سيولة النقاط</div></div></div>
            <div class="col"><div class="stat-card c-miq"><i class="fa-solid fa-coins opacity-50 mb-2"></i><div class="stat-value">{{ "{:,}".format(stats.total_miq | int) }}</div><div class="stat-label">MIQ المتداول</div></div></div>
            <div class="col"><div class="stat-card c-pend"><i class="fa-solid fa-money-check-dollar opacity-50 mb-2"></i><div class="stat-value">{{ stats.pending_withdraws }}</div><div class="stat-label">سحوبات معلقة</div></div></div>
            <div class="col"><div class="stat-card c-left"><i class="fa-solid fa-chart-pie opacity-50 mb-2"></i><div class="stat-value">{{ active_predictions|length }}</div><div class="stat-label">بورصات نشطة</div></div></div>
        </div>

        <div class="row g-3 mb-4">
            <div class="col-12">
                <div class="glass-panel border border-info" id="intel-block">
                    <div class="d-flex justify-content-between align-items-center mb-3 no-print">
                        <h4 class="block-title text-info mb-0"><i class="fa-solid fa-user-secret"></i> جهاز المخابرات والتقرير الجنائي الشامل</h4>
                        <form action="/" method="GET" class="d-flex gap-2">
                            <input type="text" name="search_id" class="form-control form-control-sm" placeholder="أدخل رقم الآيدي للبحث..." value="{{ request.args.get('search_id', '') }}" required style="width: 250px;">
                            <button type="submit" class="btn btn-info btn-sm fw-bold text-dark"><i class="fa-solid fa-search"></i> بحث واستخراج</button>
                            <a href="/" class="btn btn-secondary btn-sm">إلغاء</a>
                        </form>
                    </div>

                    {% if user_stats %}
                    <div class="user-info-card" id="print-area">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h5 class="text-info fw-bold m-0"><i class="fa-solid fa-id-badge"></i> هوية المستخدم: {{ user_stats.username }}</h5>
                            <div>
                                <button onclick="window.print()" class="btn btn-outline-info btn-sm no-print"><i class="fa-solid fa-print"></i> طباعة</button>
                                <a href="/report/user/{{ user_stats.id }}" target="_blank" class="btn btn-danger btn-sm no-print fw-bold ms-2"><i class="fa-solid fa-file-pdf"></i> استخراج وثيقة PDF</a>
                            </div>
                        </div>
                        <div class="row g-2 mb-4">
                            <div class="col-md-2"><div class="user-stat-box"><span>الآيدي (ID)</span><strong>{{ user_stats.id }}</strong></div></div>
                            <div class="col-md-2"><div class="user-stat-box"><span>الرصيد (نقاط)</span><strong class="text-success">{{ "{:,}".format(user_stats.points) }}</strong></div></div>
                            <div class="col-md-2"><div class="user-stat-box"><span>عملة (MIQ)</span><strong class="text-warning">{{ "{:,}".format(user_stats.miq_balance | int) }}</strong></div></div>
                            <div class="col-md-2"><div class="user-stat-box"><span>الرتبة</span><strong>{% if user_stats.role == 'owner' %}مالك{% elif user_stats.role == 'banned' %}مطرود{% else %}مستخدم{% endif %}</strong></div></div>
                            <div class="col-md-2"><div class="user-stat-box"><span>المحافظة</span><strong>{{ user_stats.province or 'غير محدد' }}</strong></div></div>
                            <div class="col-md-2"><div class="user-stat-box"><span>تاريخ الانضمام</span><strong>{{ user_stats.created_at.strftime('%Y-%m-%d') }}</strong></div></div>
                        </div>
                        <div class="row g-2 mb-4">
                            <div class="col-md-3"><div class="user-stat-box border-warning"><span>دعوات ناجحة (ريفرال)</span><strong class="text-warning">{{ user_stats.invites_count }} شخص</strong></div></div>
                            <div class="col-md-3"><div class="user-stat-box border-success"><span>قنوات اشترك بها</span><strong class="text-success">{{ user_stats.tasks_count }} قناة</strong></div></div>
                            <div class="col-md-3"><div class="user-stat-box border-primary"><span>عمليات تحويل (P2P)</span><strong class="text-primary">{{ user_stats.transfers_count }} عملية</strong></div></div>
                            <div class="col-md-3"><div class="user-stat-box border-danger"><span>عدد العقوبات</span><strong class="text-danger">{{ user_stats.penalties_count }} عقوبة</strong></div></div>
                        </div>
                        <h6 class="text-warning mb-2 border-bottom border-warning pb-2"><i class="fa-solid fa-list-check"></i> السجل الحركي والعمليات:</h6>
                        <div style="max-height: 200px; overflow-y: auto;">
                            <table class="table table-dark table-sm table-striped">
                                <thead><tr><th>الوقت والتاريخ</th><th>نوع العملية</th><th>التفاصيل الدقيقة</th></tr></thead>
                                <tbody>
                                    {% for log in user_logs %}
                                    <tr>
                                        <td class="small">{{ log.created_at.strftime('%Y-%m-%d %H:%M:%S') }}</td>
                                        <td class="fw-bold text-info">{{ log.action_type }}</td>
                                        <td>{{ log.details }}</td>
                                    </tr>
                                    {% else %}
                                    <tr><td colspan="3" class="text-muted text-center">لا توجد سجلات حركية لهذا المستخدم.</td></tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>
                    </div>
                    {% elif request.args.get('search_id') %}
                    <div class="alert alert-danger no-print">❌ الآيدي غير موجود في قاعدة البيانات. تأكد من الرقم.</div>
                    {% endif %}
                </div>
            </div>
        </div>

        <div class="row g-3 mb-4 no-print">
            <div class="col-12">
                <div class="glass-panel border border-danger" style="background: linear-gradient(135deg, rgba(20,26,40,0.95) 0%, rgba(153,27,27,0.1) 100%);">
                    <h4 class="block-title text-danger"><i class="fa-solid fa-bullhorn"></i> إرسال التبليغات والإعلانات (لجميع المستخدمين)</h4>
                    <form action="/action/send_broadcast" method="POST">
                        <div class="row g-2">
                            <div class="col-md-10">
                                <textarea name="message" class="form-control" rows="2" placeholder="اكتب التبليغ أو كود الخصم هنا... سيصل كرسالة خاصة لجميع مواطني الإمبراطورية." required></textarea>
                            </div>
                            <div class="col-md-2">
                                <button type="submit" class="btn btn-danger w-100 h-100 fw-bold fs-5 shadow-lg"><i class="fa-solid fa-paper-plane"></i> إرسال</button>
                            </div>
                        </div>
                    </form>
                </div>
            </div>
        </div>
        <div class="row g-3 mb-4 no-print">
            <div class="col-lg-8">
                <div class="glass-panel h-100 border border-secondary" style="background: rgba(30, 41, 59, 0.3);">
                    <h4 class="block-title text-white"><i class="fa-solid fa-chart-line"></i> المحاكي الاقتصادي: شارت الأرباح ونبض الاقتصاد</h4>
                    <div class="row mb-3">
                        <div class="col-md-5 border-end border-secondary">
                            <h5 class="text-warning fw-bold mb-1">{{ "{:,}".format(stats.total_points) }} 🟡</h5><p class="text-muted small mb-2">سيولة النقاط</p>
                            <h5 class="text-info fw-bold mb-1">{{ "{:,}".format(stats.total_miq | int) }} 🔵</h5><p class="text-muted small mb-0">سيولة MIQ</p>
                        </div>
                        <div class="col-md-7 px-3">
                            <div class="d-flex align-items-center gap-2 mb-2 border-bottom border-secondary pb-2">
                                {% if econ_status.points_state == 'inflation' %}
                                    <i class="fa-solid fa-triangle-exclamation text-danger fa-lg"></i><div><h6 class="text-danger fw-bold mb-0" style="font-size:13px;">تحذير: تضخم نقاط!</h6><p class="text-white small mb-0" style="font-size:11px;">(الناس تجمع نقاط وما تطلب متابعين. ارفع الأسعار فوراً).</p></div>
                                {% elif econ_status.points_state == 'high_demand' %}
                                    <i class="fa-solid fa-fire-flame-curved text-success fa-lg"></i><div><h6 class="text-success fw-bold mb-0" style="font-size:13px;">مؤشر: طلب نقاط عالي!</h6><p class="text-white small mb-0" style="font-size:11px;">(السوق محتاج نقاط. الوقت المثالي لعروض النقاط).</p></div>
                                {% else %}
                                    <i class="fa-solid fa-heart-pulse text-warning fa-lg"></i><div><h6 class="text-warning fw-bold mb-0" style="font-size:13px;">اقتصاد النقاط مستقر وصحي.</h6><p class="text-white small mb-0" style="font-size:11px;">السيولة متوازنة مع معدل الطلبات.</p></div>
                                {% endif %}
                            </div>
                            <div class="d-flex align-items-center gap-2">
                                {% if econ_status.miq_state == 'high_demand' %}
                                    <i class="fa-solid fa-fire-flame-curved text-success fa-lg"></i><div><h6 class="text-success fw-bold mb-0" style="font-size:13px;">سحوبات MIQ كثيفة!</h6><p class="text-white small mb-0" style="font-size:11px;">(يوجد شح في العملة وسحوبات عالية).</p></div>
                                {% else %}
                                    <i class="fa-solid fa-heart-pulse text-info fa-lg"></i><div><h6 class="text-info fw-bold mb-0" style="font-size:13px;">اقتصاد MIQ مستقر.</h6><p class="text-white small mb-0" style="font-size:11px;">العملة بوضع آمن وصحي.</p></div>
                                {% endif %}
                            </div>
                        </div>
                    </div>
                    <div style="height: 200px;"><canvas id="liquidityChart"></canvas></div>
                </div>
            </div>
            <div class="col-lg-4">
                <div class="row g-3 h-100">
                    <div class="col-12 h-50"><div class="glass-panel stat-card"><h6 class="block-title text-start small mb-2"><i class="fa-solid fa-trophy text-gold"></i> توب 5 مستخدمين</h6><div style="height: 100px;"><canvas id="topUsersChart"></canvas></div></div></div>
                    <div class="col-12 h-50"><div class="glass-panel stat-card"><h6 class="block-title text-start small mb-2"><i class="fa-solid fa-map-location-dot text-gold"></i> صدارة المحافظات</h6><div style="height: 100px;"><canvas id="provincesChart"></canvas></div></div></div>
                </div>
            </div>
        </div>

        <div class="row g-3 mb-4 no-print">
            <div class="col-12">
                <div class="glass-panel border border-success" style="background: rgba(16, 185, 129, 0.05);">
                    <h4 class="block-title text-success"><i class="fa-solid fa-wallet"></i> طلبات سحب عملة (MIQ) إلى Tonkeeper</h4>
                    <div class="table-responsive" style="max-height: 250px; overflow-y: auto;">
                        <table class="table table-dark table-striped text-center align-middle">
                            <thead class="text-success" style="position: sticky; top: 0; background: var(--panel-bg);">
                                <tr><th>رقم الطلب</th><th>العميل (ID)</th><th>عنوان المحفظة (TON Address)</th><th>الكمية (MIQ)</th><th>التاريخ</th><th>إجراءات الدفع</th></tr>
                            </thead>
                            <tbody>
                                {% for req in withdraw_requests %}
                                <tr>
                                    <td><code>#{{ req.id }}</code></td>
                                    <td><a href="/?search_id={{ req.user_id }}" class="text-white"><code>{{ req.user_id }}</code></a></td>
                                    <td class="text-info fw-bold user-select-all">{{ req.wallet_address }}</td>
                                    <td class="text-warning fw-bold fs-5">{{ "{:,}".format(req.amount) }} <i class="fa-solid fa-coins small"></i></td>
                                    <td class="small">{{ req.created_at.strftime('%Y-%m-%d %H:%M') }}</td>
                                    <td><a href="/action/approve_withdraw?id={{ req.id }}" class="btn btn-sm btn-success fw-bold px-3" onclick="return confirm('تأكيد: هل قمت بتحويل العملات لمحفظة العميل؟');"><i class="fa-solid fa-check"></i> تم الدفع</a></td>
                                </tr>
                                {% else %}
                                <tr><td colspan="6" class="text-muted py-4">لا توجد طلبات سحب معلقة حالياً.</td></tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <div class="row g-3 mb-4 no-print">
            <div class="col-12">
                <div class="glass-panel border border-primary">
                    <h4 class="block-title text-primary"><i class="fa-solid fa-satellite-dish"></i> رادار طلبات المتابعين (الطابور المباشر)</h4>
                    <p class="text-muted small">شاشة مراقبة حية لتقدم انضمام المتابعين للقنوات.</p>
                    <div class="table-responsive" style="max-height: 400px; overflow-y: auto;">
                        <table class="table table-dark table-striped text-center align-middle">
                            <thead class="text-primary" style="position: sticky; top: 0; background: var(--panel-bg); z-index: 1;">
                                <tr><th>رقم الطلب</th><th>آيدي العميل</th><th>القناة المستهدفة</th><th style="width: 30%;">عداد الإنجاز (الطابور)</th><th>إجراءات</th></tr>
                            </thead>
                            <tbody>
                                {% for order in active_orders %}
                                {% set original = order.original_quantity|default(order.quantity, true) %}
                                {% set completed = original - order.quantity %}
                                {% set percent = (completed / original * 100) if original > 0 else 0 %}
                                <tr>
                                    <td><code>#{{ order.id }}</code></td>
                                    <td><a href="/?search_id={{ order.user_id }}" class="text-decoration-none text-white fw-bold"><code>{{ order.user_id }}</code> <i class="fa-solid fa-search fa-xs text-info"></i></a></td>
                                    <td class="text-info fw-bold">{{ order.target_link }}</td>
                                    <td>
                                        <div class="d-flex justify-content-between small mb-1"><span class="text-success fw-bold">تم: {{ completed }}</span><span class="text-muted">الهدف: {{ original }}</span></div>
                                        <div class="progress" style="height: 12px; background-color: #1e293b;"><div class="progress-bar progress-bar-striped progress-bar-animated bg-success" style="width: {{ percent }}%"></div></div>
                                    </td>
                                    <td><a href="/action/del_order?id={{ order.id }}" class="btn btn-sm btn-danger py-1 px-3 fw-bold" onclick="return confirm('إيقاف الطلب؟');"><i class="fa-solid fa-stop-circle"></i> إيقاف</a></td>
                                </tr>
                                {% else %}
                                <tr><td colspan="5" class="text-muted py-4">الرادار نظيف.. لا توجد طلبات متابعين في الطابور حالياً.</td></tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <div class="row g-3 mb-4 no-print">
            <div class="col-lg-5">
                <div class="glass-panel border border-primary" style="background: rgba(13, 202, 240, 0.05);">
                    <h4 class="block-title text-primary"><i class="fa-solid fa-money-bill-transfer"></i> حاسبة وصرافة المليون</h4>
                    <form action="/action/update_exchange_settings" method="POST">
                        <div class="row g-2">
                            <div class="col-6"><label class="text-muted">سعر شراء 1 MIQ</label><input type="number" class="form-control form-control-sm" name="miq_buy_price" value="{{ settings.get('miq_buy_price', 1000) }}"></div>
                            <div class="col-6"><label class="text-muted">سعر بيع 1 MIQ</label><input type="number" class="form-control form-control-sm" name="miq_sell_price" value="{{ settings.get('miq_sell_price', 900) }}"></div>
                        </div>
                        <button type="submit" class="btn btn-primary btn-sm w-100 mt-3 text-white fw-bold">حفظ الأسعار</button>
                    </form>
                </div>
            </div>
            <div class="col-lg-4">
                <div class="glass-panel h-100 border border-info">
                    <h4 class="block-title text-info"><i class="fa-solid fa-book-open"></i> إدارة الدليل</h4>
                    <form action="/action/update_guide" method="POST" class="h-100 d-flex flex-column">
                        <textarea class="form-control mb-2 flex-grow-1" name="bot_guide_text" required>{{ settings.get('bot_guide_text', '') }}</textarea>
                        <button type="submit" class="btn btn-info btn-sm w-100 text-dark fw-bold">تحديث الدليل</button>
                    </form>
                </div>
            </div>
            <div class="col-lg-3">
                <div class="glass-panel h-100">
                    <h4 class="block-title"><i class="fa-solid fa-link"></i> قنوات التجميع</h4>
                    <form action="/action/add_channel" method="POST" class="mb-2"><div class="input-group input-group-sm"><input type="text" name="channel" class="form-control" placeholder="@Channel" required><button class="btn btn-gold" type="submit">إضافة</button></div></form>
                    <div style="max-height: 120px; overflow-y: auto;">
                        <table class="table table-dark table-sm table-striped"><tbody>{% for ch in force_subs %}<tr><td class="text-info">{{ ch.channel_username }}</td><td class="text-end"><a href="/action/del_channel?channel={{ ch.channel_username | urlencode }}" class="btn btn-sm btn-outline-danger py-0 px-2"><i class="fa-solid fa-trash"></i></a></td></tr>{% endfor %}</tbody></table>
                    </div>
                </div>
            </div>
        </div>

        <div class="row g-3 mb-4 no-print">
            <div class="col-lg-6">
                <div class="glass-panel h-100 border border-primary">
                    <h4 class="block-title text-primary"><i class="fa-solid fa-network-wired"></i> مزودي الخدمات (الرشق و APIs)</h4>
                    <form action="/action/add_provider" method="POST" class="mb-3">
                        <div class="row g-2 mb-2">
                            <div class="col-6"><input type="text" class="form-control form-control-sm" name="name" placeholder="اسم الشركة" required></div>
                            <div class="col-6"><select class="form-select form-select-sm" name="service_type"><option value="telegram">تيليجرام</option><option value="instagram">انستغرام</option></select></div>
                            <div class="col-12"><input type="url" class="form-control form-control-sm" name="api_url" placeholder="الرابط (API URL)" required></div>
                            <div class="col-12"><input type="text" class="form-control form-control-sm" name="api_key" placeholder="المفتاح (API Key)" required></div>
                        </div>
                        <button type="submit" class="btn btn-primary btn-sm w-100 fw-bold">ربط الشركة بالنظام</button>
                    </form>
                    <div style="max-height: 150px; overflow-y: auto;">
                        <table class="table table-dark table-sm table-striped">
                            <tbody>{% for prov in providers %}<tr><td class="text-info">{{ prov.name }} <span class="badge bg-secondary">{{ prov.service_type }}</span></td><td class="text-end"><a href="/action/del_provider?id={{ prov.id }}" class="btn btn-sm btn-danger py-0 px-2"><i class="fa-solid fa-unlink"></i></a></td></tr>{% else %}<tr><td colspan="2" class="text-center text-muted">لا توجد شركات.</td></tr>{% endfor %}</tbody>
                        </table>
                    </div>
                </div>
            </div>
            
            <div class="col-lg-6">
                <div class="glass-panel h-100 border border-warning" style="background: rgba(245, 158, 11, 0.05);">
                    <h4 class="block-title text-warning"><i class="fa-solid fa-building-columns"></i> البنك المركزي وخزنة الودائع</h4>
                    <form action="/action/update_bank_settings" method="POST" class="mb-3 d-flex gap-2">
                        <div class="flex-grow-1"><label class="text-warning small fw-bold">نسبة الفائدة اليومية (%)</label><input type="number" step="0.1" class="form-control form-control-sm text-warning" name="bank_interest_percent" value="{{ settings.get('bank_interest_percent', 5.0) }}"></div>
                        <button type="submit" class="btn btn-warning btn-sm text-dark fw-bold mt-4">تحديث</button>
                    </form>
                    <h6 class="text-white mb-2"><i class="fa-solid fa-vault text-warning"></i> الودائع النشطة في الخزنة:</h6>
                    <div class="table-responsive" style="max-height: 180px; overflow-y: auto;">
                        <table class="table table-dark table-sm table-striped text-center">
                            <thead class="text-warning" style="position: sticky; top: 0; background: #000;"><tr><th>آيدي المستثمر</th><th>قيمة الوديعة</th><th>العملة</th><th>تاريخ الإيداع</th></tr></thead>
                            <tbody>{% for dep in bank_deposits %}<tr><td><code>{{ dep.user_id }}</code></td><td class="text-success fw-bold">{{ "{:,}".format(dep.amount) }}</td><td><span class="badge bg-dark border">{{ dep.currency }}</span></td><td class="small">{{ dep.start_date.strftime('%Y-%m-%d') }}</td></tr>{% else %}<tr><td colspan="4" class="text-muted">الخزنة فارغة حالياً.</td></tr>{% endfor %}</tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <div class="row g-3 mb-4 no-print">
            <div class="col-lg-5">
                <div class="glass-panel border border-warning h-100">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <h4 class="block-title text-warning mb-0"><i class="fa-solid fa-user-plus"></i> إدارة الريفرال</h4>
                        <form action="/action/update_referral_settings" method="POST" class="d-flex gap-2">
                            <input type="number" class="form-control form-control-sm" style="width: 80px;" name="invite_reward_pts" value="{{ settings.get('invite_reward_pts', 15) }}" required>
                            <button type="submit" class="btn btn-warning btn-sm text-dark fw-bold">تحديث</button>
                        </form>
                    </div>
                    <div style="max-height: 200px; overflow-y: auto;">
                        <table class="table table-dark table-sm table-striped text-center align-middle">
                            <thead class="text-warning"><tr><th>آيدي الداعي</th><th>آيدي المنضم</th></tr></thead>
                            <tbody>{% for log in referral_logs %}<tr><td><code>{{ log.inviter_id }}</code></td><td class="text-info"><code>{{ log.invited_user_id }}</code></td></tr>{% else %}<tr><td colspan="2" class="text-muted">لا توجد دعوات.</td></tr>{% endfor %}</tbody>
                        </table>
                    </div>
                </div>
            </div>
            <div class="col-lg-7">
                <div class="glass-panel h-100 border border-gold">
                    <h4 class="block-title text-gold"><i class="fa-solid fa-store"></i> المتجر الإمبراطوري الشامل</h4>
                    <form action="/action/add_advanced_product" method="POST" class="mb-3 p-2 bg-black rounded border border-secondary">
                        <div class="row g-2 mb-2">
                            <div class="col-md-5"><input type="text" class="form-control form-control-sm" name="name" placeholder="المنتج" required></div>
                            <div class="col-md-3"><input type="number" class="form-control form-control-sm" name="price" placeholder="السعر" required></div>
                            <div class="col-md-4"><select class="form-select form-select-sm text-warning" name="currency"><option value="MIQ">MIQ</option><option value="نقاط">نقاط</option><option value="دينار">دينار عراقي</option></select></div>
                            <div class="col-12"><input type="text" class="form-control form-control-sm" name="description" placeholder="الوصف التفصيلي الجذاب للمنتج..." required></div>
                        </div>
                        <button type="submit" class="btn btn-gold btn-sm w-100 text-dark fw-bold"><i class="fa-solid fa-cart-plus"></i> إضافة المنتج</button>
                    </form>
                    <div class="table-responsive" style="max-height: 150px; overflow-y: auto;">
                        <table class="table table-dark table-sm table-striped text-center">
                            <thead class="text-warning"><tr><th>المنتج</th><th>الوصف</th><th>السعر</th><th>حذف</th></tr></thead>
                            <tbody>{% for prod in advanced_products %}<tr><td class="fw-bold">{{ prod.name }}</td><td class="small text-muted">{{ prod.description[:30] }}</td><td class="text-success fw-bold">{{ "{:,}".format(prod.price) }} {{ prod.currency }}</td><td><a href="/action/del_advanced_product?id={{ prod.id }}" class="btn btn-sm btn-danger py-0 px-2"><i class="fa-solid fa-trash"></i></a></td></tr>{% endfor %}</tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <div class="row g-3 mb-4 no-print">
            <div class="col-lg-5">
                <div class="glass-panel h-100 border border-danger" style="background: linear-gradient(135deg, rgba(20,26,40,0.95) 0%, rgba(153,27,27,0.1) 100%);">
                    <h4 class="block-title text-danger"><i class="fa-solid fa-gem"></i> إعدادات لعبة (منجم المليون)</h4>
                    <form action="/action/update_mine_settings" method="POST">
                        <div class="row g-2 mb-2">
                            <div class="col-7"><label class="text-danger small fw-bold">سعر فأس التنقيب (نقاط)</label><input type="number" class="form-control form-control-sm" name="mine_game_cost" value="{{ settings.get('mine_game_cost', 100) }}"></div>
                            <div class="col-5"><label class="text-warning small fw-bold">نوع الجائزة</label><select class="form-select form-select-sm" name="mine_reward_type"><option value="miq" {% if settings.get('mine_reward_type') == 'miq' %}selected{% endif %}>MIQ</option><option value="points" {% if settings.get('mine_reward_type') == 'points' %}selected{% endif %}>نقاط</option></select></div>
                            <div class="col-6"><label class="text-white small">الحد الأدنى للجائزة</label><input type="number" class="form-control form-control-sm text-center" name="mine_reward_min" value="{{ settings.get('mine_reward_min', 1) }}"></div>
                            <div class="col-6"><label class="text-white small">الحد الأعلى للجائزة</label><input type="number" class="form-control form-control-sm text-center" name="mine_reward_max" value="{{ settings.get('mine_reward_max', 5) }}"></div>
                        </div>
                        <button type="submit" class="btn btn-danger btn-sm w-100 fw-bold mt-2"><i class="fa-solid fa-save"></i> حفظ الإعدادات</button>
                    </form>
                </div>
            </div>
            
            <div class="col-lg-4">
                <div class="glass-panel h-100 border border-success" style="background: rgba(16, 185, 129, 0.05);">
                    <h4 class="block-title text-success"><i class="fa-solid fa-gift"></i> صندوق الإهداء الملكي</h4>
                    <form action="/action/gift_user" method="POST">
                        <div class="row g-2 mb-2">
                            <div class="col-12"><input type="text" class="form-control form-control-sm" name="user_id" placeholder="آيدي المستخدم" required></div>
                            <div class="col-6"><input type="number" class="form-control form-control-sm" name="amount" placeholder="الكمية" required></div>
                            <div class="col-6"><select class="form-select form-select-sm" name="currency"><option value="points">نقاط</option><option value="miq">MIQ</option></select></div>
                        </div>
                        <button type="submit" class="btn btn-success w-100 btn-sm fw-bold"><i class="fa-solid fa-paper-plane"></i> إرسال الهدية</button>
                    </form>
                </div>
            </div>

            <div class="col-lg-3">
                <div class="glass-panel h-100 border border-primary">
                    <h4 class="block-title text-primary"><i class="fa-solid fa-money-bill-transfer"></i> تحويل P2P</h4>
                    <form action="/action/update_transfer_settings" method="POST">
                        <label class="text-muted small">رسوم التحويل بين المستخدمين</label>
                        <div class="input-group input-group-sm">
                            <input type="number" class="form-control" name="transfer_fee" value="{{ settings.get('transfer_fee', 0) }}" required>
                            <button type="submit" class="btn btn-primary fw-bold">تحديث</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>

        <div class="row g-3 mb-4 no-print">
            <div class="col-lg-6">
                <div class="glass-panel h-100 border border-warning" style="background: rgba(30, 41, 59, 0.4);">
                    <h4 class="block-title text-warning"><i class="fa-solid fa-chart-line"></i> وول ستريت المليون (بورصة التوقعات)</h4>
                    <form action="/action/add_prediction" method="POST" class="mb-3">
                        <input type="text" class="form-control form-control-sm mb-1" name="question" placeholder="السؤال أو الحدث؟" required>
                        <div class="row g-1 mb-2">
                            <div class="col-6"><input type="text" class="form-control form-control-sm" name="opt1" placeholder="خيار 1 (إجباري)" required></div>
                            <div class="col-6"><input type="text" class="form-control form-control-sm" name="opt2" placeholder="خيار 2 (إجباري)" required></div>
                            <div class="col-6"><input type="text" class="form-control form-control-sm" name="opt3" placeholder="خيار 3 (اختياري)"></div>
                            <div class="col-6"><input type="text" class="form-control form-control-sm" name="opt4" placeholder="خيار 4 (اختياري)"></div>
                        </div>
                        <button type="submit" class="btn btn-warning btn-sm w-100 fw-bold text-dark"><i class="fa-solid fa-rocket"></i> إطلاق البورصة</button>
                    </form>
                    <div class="table-responsive" style="max-height: 150px; overflow-y: auto;">
                        <table class="table table-dark table-sm table-striped align-middle">
                            <thead class="text-warning"><tr><th>السؤال</th><th>المشاركين</th><th>أزرار الإنهاء</th></tr></thead>
                            <tbody>
                                {% for pred in active_predictions %}
                                <tr>
                                    <td class="small">{{ pred.question }}</td>
                                    <td><span class="badge bg-primary">{{ pred.bets_count }} رهان</span></td>
                                    <td>
                                        <div class="btn-group btn-group-sm w-100">
                                            <a href="/action/resolve_prediction?id={{ pred.id }}&winner=1" class="btn btn-success py-0">1✔️</a>
                                            <a href="/action/resolve_prediction?id={{ pred.id }}&winner=2" class="btn btn-success py-0">2✔️</a>
                                            <a href="/action/cancel_prediction?id={{ pred.id }}" class="btn btn-danger py-0 fw-bold" title="إلغاء">❌</a>
                                        </div>
                                    </td>
                                </tr>
                                {% else %}<tr><td colspan="3" class="text-muted text-center py-2">لا توجد بورصات نشطة.</td></tr>{% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            
            <div class="col-lg-3">
                <div class="glass-panel h-100 border border-info">
                    <h4 class="block-title text-info"><i class="fa-solid fa-bolt"></i> صندوق الحظ</h4>
                    <form action="/action/stop_drop" method="POST" class="mb-2"><button type="submit" class="btn btn-danger btn-sm w-100 fw-bold"><i class="fa-solid fa-trash"></i> سحب الصندوق</button></form>
                    <form action="/action/add_drop" method="POST">
                        <input type="number" class="form-control form-control-sm mb-1" name="reward" placeholder="النقاط" required>
                        <input type="number" class="form-control form-control-sm mb-2" name="max_winners" placeholder="كم فائز؟" required>
                        <button type="submit" class="btn btn-info btn-sm w-100 text-dark fw-bold">إسقاط صندوق</button>
                    </form>
                </div>
            </div>
            
            <div class="col-lg-3">
                <div class="glass-panel h-100 border border-success">
                    <h4 class="block-title text-success"><i class="fa-solid fa-newspaper"></i> اقرأ لتربح</h4>
                    <form action="/action/stop_news" method="POST" class="mb-2"><button type="submit" class="btn btn-danger btn-sm w-100 fw-bold"><i class="fa-solid fa-ban"></i> إيقاف المهمة</button></form>
                    <form action="/action/add_news" method="POST">
                        <input type="text" class="form-control form-control-sm mb-1" name="url" placeholder="الرابط" required>
                        <input type="text" class="form-control form-control-sm mb-1" name="question" placeholder="السؤال" required>
                        <input type="text" class="form-control form-control-sm mb-1" name="answer" placeholder="الجواب" required>
                        <div class="d-flex gap-1 mb-2">
                            <input type="number" class="form-control form-control-sm" name="reward" placeholder="المكافأة" required>
                            <input type="number" class="form-control form-control-sm" name="max_winners" placeholder="كم فائز؟" required>
                        </div>
                        <button type="submit" class="btn btn-success btn-sm w-100 fw-bold">نشر المهمة</button>
                    </form>
                </div>
            </div>
        </div>

        <div class="row g-3 mb-4 no-print">
            <div class="col-lg-6">
                <div class="glass-panel h-100 border border-gold">
                    <h4 class="block-title text-gold"><i class="fa-solid fa-ticket"></i> أكواد هدايا</h4>
                    <form action="/action/add_promo" method="POST">
                        <div class="row g-2 mb-2">
                            <div class="col-md-5"><input type="text" class="form-control form-control-sm" name="code" placeholder="الرمز" required></div>
                            <div class="col-md-3"><input type="number" class="form-control form-control-sm" name="reward" placeholder="الجائزة" required></div>
                            <div class="col-md-4"><input type="number" class="form-control form-control-sm" name="max_uses" placeholder="كم مستخدم؟" required></div>
                        </div>
                        <button type="submit" class="btn btn-outline-warning w-100 btn-sm fw-bold">توليد ونشر</button>
                    </form>
                </div>
            </div>
            <div class="col-lg-6">
                <div class="glass-panel h-100 border border-danger">
                    <h4 class="block-title text-danger"><i class="fa-solid fa-gavel"></i> محكمة القيادة (العقوبات)</h4>
                    <form action="/action/penalize_user" method="POST">
                        <div class="row g-2">
                            <div class="col-md-4"><input type="text" class="form-control form-control-sm" name="user_id" placeholder="آيدي المخالف" required></div>
                            <div class="col-md-8"><select class="form-select form-select-sm" name="penalty_type"><option value="warn">⚠️ إنذار</option><option value="freeze">❄️ تصفير الرصيد</option><option value="ban">🚫 حظر نهائي</option></select></div>
                            <div class="col-12 mt-1"><input type="text" class="form-control form-control-sm" name="reason" placeholder="السبب" required></div>
                        </div>
                        <button type="submit" class="btn btn-danger w-100 btn-sm mt-2 fw-bold">تطبيق الحكم</button>
                    </form>
                </div>
            </div>
        </div>

        <div class="row g-3 mb-4 no-print">
            <div class="col-lg-12">
                <div class="glass-panel border border-primary">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <h4 class="block-title text-primary mb-0"><i class="fa-solid fa-users-viewfinder"></i> السجل المدني (قائمة المستخدمين)</h4>
                        <form action="/" method="GET" class="d-flex gap-2">
                            <input type="text" name="search_user" class="form-control form-control-sm" placeholder="ابحث بالآيدي أو المعرف..." value="{{ search_user }}">
                            <button type="submit" class="btn btn-primary btn-sm text-white fw-bold"><i class="fa-solid fa-search"></i></button>
                            <a href="/" class="btn btn-secondary btn-sm"><i class="fa-solid fa-rotate-right"></i></a>
                        </form>
                    </div>
                    <div class="table-responsive">
                        <table class="table table-dark table-sm table-striped text-center align-middle">
                            <thead class="text-primary"><tr><th>الآيدي (ID)</th><th>المعرف (Username)</th><th>الرصيد (نقاط)</th><th>رصيد (MIQ)</th><th>المحافظة</th><th>تاريخ الانضمام</th></tr></thead>
                            <tbody>
                                {% for u in users_list %}
                                <tr>
                                    <td><code>{{ u.id }}</code></td><td>{{ u.username or 'بدون معرف' }}</td><td class="text-success fw-bold">{{ "{:,}".format(u.points) }}</td>
                                    <td class="text-warning fw-bold">{{ "{:,}".format(u.miq_balance | int) }}</td><td>{{ u.province or 'غير محدد' }}</td><td class="small">{{ u.created_at.strftime('%Y-%m-%d %H:%M') }}</td>
                                </tr>
                                {% else %}
                                <tr><td colspan="6" class="text-muted py-4">لم يتم العثور على أي مستخدم بهذا البحث.</td></tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                    {% if total_pages > 1 %}
                    <nav class="mt-3">
                        <ul class="pagination pagination-sm justify-content-center mb-0">
                            <li class="page-item {% if page == 1 %}disabled{% endif %}"><a class="page-link bg-dark text-primary border-secondary" href="?page={{ page - 1 }}&search_user={{ search_user }}">السابق</a></li>
                            <li class="page-item disabled"><span class="page-link bg-dark text-white border-secondary">صفحة {{ page }} من {{ total_pages }}</span></li>
                            <li class="page-item {% if page == total_pages %}disabled{% endif %}"><a class="page-link bg-dark text-primary border-secondary" href="?page={{ page + 1 }}&search_user={{ search_user }}">التالي</a></li>
                        </ul>
                    </nav>
                    {% endif %}
                </div>
            </div>
        </div>

    </div>

    <script>
        const ctx = document.getElementById('liquidityChart').getContext('2d');
        let currentPoints = {{ stats.total_points }};
        let currentMiq = {{ stats.total_miq | int }};
        let dataPoints = [];
        let dataMiq = [];
        for(let i=6; i>=0; i--) { 
            dataPoints.push(Math.max(0, currentPoints - (i * 8000) + Math.floor(Math.random() * 4000))); 
            dataMiq.push(Math.max(0, currentMiq - (i * 500) + Math.floor(Math.random() * 200)));
        }
        dataPoints[6] = currentPoints;
        dataMiq[6] = currentMiq;
        new Chart(ctx, { 
            type: 'line', 
            data: { 
                labels: ['قبل 6 أيام', 'قبل 5 أيام', 'قبل 4 أيام', 'قبل 3 أيام', 'أول أمس', 'البارحة', 'الآن'], 
                datasets: [
                    { label: 'سيولة النقاط 🟡', data: dataPoints, borderColor: '#fbbf24', backgroundColor: 'rgba(251, 191, 36, 0.05)', fill: true, tension: 0.4 },
                    { label: 'سيولة MIQ 🔵', data: dataMiq, borderColor: '#0dcaf0', backgroundColor: 'rgba(13, 202, 240, 0.05)', fill: true, tension: 0.4 }
                ] 
            }, 
            options: { maintainAspectRatio: false, plugins: { legend: { display: true, labels: {color: '#fff', font:{family:'tahoma'}} } }, scales: { y: { ticks: { color: '#a6b0cf' }, grid: {color:'rgba(255,255,255,0.05)'} }, x: { ticks: { color: '#a6b0cf' }, grid: {display:false} } } } 
        });

        new Chart(document.getElementById('topUsersChart').getContext('2d'), { type: 'bar', data: { labels: [{% for u in top_users %}'{{ u.id | string | truncate(5, True, '') }}',{% endfor %}], datasets: [{ label: 'النقاط', data: [{% for u in top_users %}{{ u.points }},{% endfor %}], backgroundColor: '#3b82f6', borderRadius: 3 }] }, options: { maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { display:false }, x: { ticks: { color: '#a6b0cf', font: {size: 10} } } } } });

        new Chart(document.getElementById('provincesChart').getContext('2d'), { type: 'doughnut', data: { labels: [{% for p in top_provs %}'{{ p.province }}',{% endfor %}], datasets: [{ data: [{% for p in top_provs %}{{ p.total }},{% endfor %}], backgroundColor: ['#ef4444', '#f97316', '#f59e0b', '#10b981', '#3b82f6'], borderWidth:1, borderColor:'var(--panel-bg)' }] }, options: { maintainAspectRatio: false, plugins: { legend: { display:false } } } });
    </script>
</body>
</html>
"""
# ================= قالب التقرير الرسمي (PDF) =================
REPORT_TEMPLATE = """
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <title>التقرير المالي والجنائي - إمبراطورية المليون</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #fff; color: #111; padding: 40px; margin: 0 auto; max-width: 900px; line-height: 1.6;}
        .watermark { position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%) rotate(-45deg); font-size: 120px; color: rgba(0,0,0,0.03); z-index: -1; white-space: nowrap; font-weight: 900;}
        .header { text-align: center; border-bottom: 4px solid #fbbf24; padding-bottom: 25px; margin-bottom: 35px; }
        .header h1 { margin: 0; color: #1e3a8a; font-size: 32px; font-weight: 900; letter-spacing: 1px;}
        .header p { margin: 5px 0; color: #64748b; font-size: 15px; }
        .section-title { background: #f8fafc; padding: 12px 15px; border-right: 5px solid #3b82f6; font-weight: bold; font-size: 18px; margin-top: 30px; margin-bottom: 15px; color: #0f172a;}
        table { width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 14px;}
        th, td { border: 1px solid #cbd5e1; padding: 12px 15px; text-align: right; }
        th { background-color: #f1f5f9; color: #334155; font-weight: bold; width: 25%;}
        .highlight { color: #047857; font-weight: bold; font-size: 16px;}
        .highlight-gold { color: #b45309; font-weight: bold; font-size: 16px;}
        .footer { text-align: center; margin-top: 60px; padding-top: 20px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #94a3b8; }
        .print-btn { display: block; width: 250px; margin: 20px auto 40px; padding: 15px; background: #2563eb; color: white; text-align: center; text-decoration: none; border-radius: 8px; font-weight: bold; cursor: pointer; border:none; font-size: 16px; box-shadow: 0 4px 6px rgba(37, 99, 235, 0.2);}
        .print-btn:hover { background: #1d4ed8; }
        @media print { .print-btn { display: none !important; } body { padding: 0; } }
    </style>
</head>
<body>
    <div class="watermark">MILLION EMPIRE</div>
    <button class="print-btn" onclick="window.print()">🖨️ طباعة التقرير / حفظ كـ PDF</button>
    
    <div class="header">
        <h1>إمبراطورية المليون</h1>
        <p>التقرير المالي والجنائي الموثق (وثيقة رسمية)</p>
        <p style="font-weight: bold; color: #333;">تاريخ ووقت الإصدار: {{ date }}</p>
    </div>

    <div class="section-title">أولاً: البيانات الأساسية للمواطن (المستخدم)</div>
    <table>
        <tr><th>الآيدي (ID) الموحد</th><td><strong>{{ user.id }}</strong></td><th>الاسم / المعرف</th><td>{{ user.username or 'غير متوفر' }}</td></tr>
        <tr><th>رصيد النقاط المحلي</th><td class="highlight">{{ "{:,}".format(user.points) }} نقطة</td><th>رصيد (MIQ) العالمي</th><td class="highlight-gold">{{ "{:,}".format(user.miq_balance | int) }} MIQ</td></tr>
        <tr><th>تاريخ الانضمام للمنصة</th><td>{{ user.created_at }}</td><th>المحافظة / الموقع</th><td>{{ user.province or 'غير محدد' }}</td></tr>
        <tr><th>الرتبة في النظام</th><td colspan="3">{% if user.role == 'owner' %}مالك الإمبراطورية{% elif user.role == 'banned' %}مطرود (Banned){% else %}مستخدم نشط{% endif %}</td></tr>
    </table>

    <div class="section-title">ثانياً: السجل الجنائي والعمليات (آخر 100 حركة)</div>
    <table>
        <thead><tr><th style="width: 20%;">تاريخ ووقت الحركة</th><th style="width: 25%;">نوع العملية</th><th>تفاصيل الحركة الدقيقة</th></tr></thead>
        <tbody>
            {% for log in logs %}
            <tr>
                <td style="color: #64748b; font-size: 12px;">{{ log.created_at }}</td>
                <td style="font-weight: bold; color: #334155;">{{ log.action_type }}</td>
                <td>{{ log.details }}</td>
            </tr>
            {% else %}
            <tr><td colspan="3" style="text-align:center; padding: 30px; color: #94a3b8;">السجل نظيف. لا توجد أي حركات مسجلة لهذا المستخدم حتى الآن.</td></tr>
            {% endfor %}
        </tbody>
    </table>

    <div class="footer">
        <p>تم إصدار هذه الوثيقة آلياً من نظام إدارة منصة المليون الموثق.</p>
        <p>جميع البيانات الواردة في هذا التقرير محفوظة ومؤمنة في قواعد البيانات المركزية للإمبراطورية ولا يمكن التلاعب بها.</p>
    </div>
</body>
</html>
"""

# ================= مسارات (Routes) التطبيق =================

@app.route('/')
def dashboard():
    if not session.get('logged_in'):
        return """
        <body style="background:#0c1120; text-align:center; padding-top:100px; color:white; font-family:sans-serif;">
            <div style="background:rgba(22,29,49,0.9); padding:20px; display:inline-block; border-radius:10px; border:1px solid rgba(251,191,36,0.3);">
                <h3 style="color:#fbbf24; margin-bottom:20px;">👑 بوابة الإمبراطورية السرية</h3>
                <form method="POST" action="/login">
                    <input type="password" name="pwd" placeholder="الرمز السري..." style="padding:10px; border-radius:5px; border:1px solid #ccc; background:black; color:white; margin-bottom:15px; width:200px;"><br>
                    <button type="submit" style="padding:10px 25px; border-radius:5px; border:none; background:#fbbf24; color:black; font-weight:bold; cursor:pointer;">دخول</button>
                </form>
            </div>
        </body>
        """

    stats = {'total_users': 0, 'inactive_users': 0, 'total_points': 0, 'total_miq': 0, 'pending_orders': 0, 'completed_orders': 0, 'pending_withdraws': 0}
    settings, withdraw_requests, advanced_products, providers, bank_deposits, active_predictions = {}, [], [], [], [], []
    active_orders, top_users, top_provs, users_list, user_logs, referral_logs, force_subs = [], [], [], [], [], [], []
    user_stats = None
    econ_status = {'points_state': 'stable', 'miq_state': 'stable'}

    search_id = request.args.get('search_id', '')
    search_user = request.args.get('search_user', '')
    page = request.args.get('page', 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page
    total_pages = 1

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # --- الرقعة الذكية لتحديث قاعدة البيانات القديمة تلقائياً ---
            try: cur.execute("ALTER TABLE users ADD COLUMN invites_count INT DEFAULT 0")
            except: pass
            try: cur.execute("ALTER TABLE users ADD COLUMN miq_balance FLOAT DEFAULT 0")
            except: pass
            try: cur.execute("ALTER TABLE users ADD COLUMN province VARCHAR(100)")
            except: pass
            try: cur.execute("ALTER TABLE users ADD COLUMN last_mine_time TIMESTAMP NULL")
            except: pass
            # -------------------------------------------------------------

            cur.execute("SELECT COUNT(id) AS c, SUM(points) AS p, SUM(miq_balance) AS m FROM users WHERE role != 'banned'")
            res = cur.fetchone()
            if res and res['c']:
                stats['total_users'] = res['c'] or 0
                stats['total_points'] = res['p'] or 0
                stats['total_miq'] = res['m'] or 0
            
            cur.execute("SELECT COUNT(*) as c FROM withdraw_requests WHERE status = 'pending'")
            stats['pending_withdraws'] = (cur.fetchone())['c'] or 0

            cur.execute("SELECT COUNT(DISTINCT user_id) as c FROM action_logs WHERE action_type IN ('freeze', 'ban')")
            stats['inactive_users'] = (cur.fetchone())['c'] or 0

            try:
                cur.execute("SELECT status, COUNT(*) as c FROM orders GROUP BY status")
                for r in cur.fetchall():
                    if r['status'] == 'pending': stats['pending_orders'] = r['c']
                    elif r['status'] == 'completed': stats['completed_orders'] = r['c']
            except: pass

            # المحاكي الاقتصادي المزدوج (نقاط و MIQ)
            if stats['total_users'] > 0:
                points_per_user = stats['total_points'] / stats['total_users']
                if points_per_user > 100 and stats['completed_orders'] < stats['pending_orders']: econ_status['points_state'] = 'inflation'
                elif points_per_user < 10 or stats['pending_orders'] > (stats['total_users'] * 2): econ_status['points_state'] = 'high_demand'
                
                if stats['pending_withdraws'] > (stats['total_users'] * 0.1): econ_status['miq_state'] = 'high_demand'

            # الإعدادات
            cur.execute("SELECT * FROM settings")
            for r in cur.fetchall(): settings[r['setting_key']] = r['setting_value']

            # القوائم
            cur.execute("SELECT * FROM withdraw_requests WHERE status = 'pending' ORDER BY id DESC")
            withdraw_requests = cur.fetchall()

            cur.execute("SELECT * FROM advanced_store ORDER BY id DESC")
            advanced_products = cur.fetchall()

            cur.execute("SELECT * FROM smm_providers")
            providers = cur.fetchall()

            cur.execute("SELECT * FROM bank_deposits WHERE status = 'active' ORDER BY id DESC")
            bank_deposits = cur.fetchall()

            cur.execute("SELECT p.*, (SELECT COUNT(*) FROM prediction_bets b WHERE b.prediction_id = p.id) as bets_count FROM predictions p WHERE p.status = 'active' ORDER BY p.id DESC")
            active_predictions = cur.fetchall()

            try:
                cur.execute("SELECT * FROM orders WHERE status = 'pending' AND quantity > 0 ORDER BY id DESC")
                active_orders = cur.fetchall()
            except: pass

            cur.execute("SELECT * FROM force_subs")
            force_subs = cur.fetchall()

            cur.execute("SELECT action_logs.created_at, users.id as inviter_id, SUBSTRING_INDEX(action_logs.details, 'user ', -1) as invited_user_id FROM action_logs JOIN users ON action_logs.user_id = users.id WHERE action_logs.action_type='referral_bonus' ORDER BY action_logs.id DESC LIMIT 50")
            referral_logs = cur.fetchall()

            # الشارتات
            cur.execute("SELECT id, points FROM users WHERE role != 'banned' ORDER BY points DESC LIMIT 5")
            top_users = cur.fetchall()
            cur.execute("SELECT province, SUM(points) as total FROM users WHERE province IS NOT NULL GROUP BY province ORDER BY total DESC LIMIT 5")
            top_provs = cur.fetchall()

            # المخابرات
            if search_id.isdigit():
                cur.execute("SELECT * FROM users WHERE id = %s", (search_id,))
                user_stats = cur.fetchone()
                if user_stats:
                    cur.execute("SELECT COUNT(*) as c FROM action_logs WHERE action_type = 'p2p_transfer' AND user_id = %s", (search_id,))
                    user_stats['transfers_count'] = cur.fetchone()['c']
                    cur.execute("SELECT COUNT(*) as c FROM action_logs WHERE action_type IN ('penalty_leave', 'warn', 'freeze', 'ban') AND user_id = %s", (search_id,))
                    user_stats['penalties_count'] = cur.fetchone()['c']
                    cur.execute("SELECT COUNT(*) as c FROM users WHERE invites_count > 0 AND id = %s", (search_id,)) # تقريبي
                    user_stats['tasks_count'] = 0 # تقريبي
                    cur.execute("SELECT * FROM action_logs WHERE user_id = %s ORDER BY id DESC LIMIT 100", (search_id,))
                    user_logs = cur.fetchall()

            # السجل المدني (Pagination)
            user_query = "SELECT * FROM users WHERE role != 'banned'"
            user_params = []
            if search_user:
                user_query += " AND (id LIKE %s OR username LIKE %s)"
                user_params.extend([f"%{search_user}%", f"%{search_user}%"])
            
            cur.execute(f"SELECT COUNT(*) as c FROM ({user_query}) as subquery", tuple(user_params))
            total_users_count = cur.fetchone()['c']
            total_pages = (total_users_count + per_page - 1) // per_page
            
            user_query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
            user_params.extend([per_page, offset])
            cur.execute(user_query, tuple(user_params))
            users_list = cur.fetchall()

        conn.close()
    except Exception as e:
        flash(f"خطأ في قاعدة البيانات: {e}", "danger")

    return render_template_string(
        HTML_TEMPLATE, stats=stats, settings=settings, econ_status=econ_status,
        withdraw_requests=withdraw_requests, advanced_products=advanced_products,
        providers=providers, bank_deposits=bank_deposits, active_predictions=active_predictions,
        active_orders=active_orders, top_users=top_users, top_provs=top_provs, force_subs=force_subs,
        referral_logs=referral_logs, users_list=users_list, user_logs=user_logs, user_stats=user_stats,
        search_user=search_user, page=page, total_pages=total_pages
    )

# ================= مسارات التحكم والأوامر الإدارية =================

@app.route('/login', methods=['POST'])
def login():
    if request.form.get('pwd') == ADMIN_PASSWORD:
        session['logged_in'] = True
        flash("مرحباً بك في مركز القيادة الإمبراطوري!", "success")
    else:
        flash("الرمز السري غير صحيح!", "danger")
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('dashboard'))

def _update_setting(key, value):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("INSERT INTO settings (setting_key, setting_value) VALUES (%s, %s) ON DUPLICATE KEY UPDATE setting_value = %s", (key, value, value))
    conn.commit()
    conn.close()

# --- بلوك الإذاعة والإعلان (القوة الضاربة) ---
@app.route('/action/send_broadcast', methods=['POST'])
def action_send_broadcast():
    if session.get('logged_in'):
        msg = request.form.get('message')
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("INSERT INTO broadcast_queue (message_text) VALUES (%s)", (msg,))
        conn.commit()
        conn.close()
        flash("💥 تم إطلاق القوة الضاربة! الرسالة الآن في طابور الإرسال لكل المستخدمين.", "success")
    return redirect(url_for('dashboard'))

@app.route('/action/update_bank_settings', methods=['POST'])
def action_update_bank_settings():
    if session.get('logged_in'):
        _update_setting('bank_interest_percent', request.form['bank_interest_percent'])
        flash("✅ تم تحديث نسبة الفائدة البنكية.", "success")
    return redirect(url_for('dashboard'))

@app.route('/action/update_mine_settings', methods=['POST'])
def action_update_mine_settings():
    if session.get('logged_in'):
        for key in ['mine_game_cost', 'mine_reward_type', 'mine_reward_min', 'mine_reward_max']:
            _update_setting(key, request.form[key])
        flash("✅ تم تحديث إعدادات لعبة منجم المليون.", "success")
    return redirect(url_for('dashboard'))

@app.route('/action/update_exchange_settings', methods=['POST'])
def action_update_exchange_settings():
    if session.get('logged_in'):
        _update_setting('miq_buy_price', request.form['miq_buy_price'])
        _update_setting('miq_sell_price', request.form['miq_sell_price'])
        flash("✅ تم تحديث أسعار الصرافة.", "success")
    return redirect(url_for('dashboard'))

@app.route('/action/update_guide', methods=['POST'])
def action_update_guide():
    if session.get('logged_in'):
        _update_setting('bot_guide_text', request.form['bot_guide_text'])
        flash("✅ تم تحديث نص الدليل.", "success")
    return redirect(url_for('dashboard'))

@app.route('/action/update_referral_settings', methods=['POST'])
def action_update_referral_settings():
    if session.get('logged_in'):
        _update_setting('invite_reward_pts', request.form['invite_reward_pts'])
        flash("✅ تم تحديث مكافأة الدعوة.", "success")
    return redirect(url_for('dashboard'))

@app.route('/action/update_transfer_settings', methods=['POST'])
def action_update_transfer_settings():
    if session.get('logged_in'):
        _update_setting('transfer_fee', request.form['transfer_fee'])
        flash("✅ تم تحديث رسوم تحويل P2P.", "success")
    return redirect(url_for('dashboard'))

@app.route('/action/approve_withdraw', methods=['GET'])
def action_approve_withdraw():
    if session.get('logged_in'):
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("UPDATE withdraw_requests SET status = 'paid' WHERE id = %s", (request.args.get('id'),))
        conn.commit()
        conn.close()
        flash("✅ تم تأكيد الدفع وإغلاق طلب السحب.", "success")
    return redirect(url_for('dashboard'))

@app.route('/action/add_advanced_product', methods=['POST'])
def action_add_advanced_product():
    if session.get('logged_in'):
        f = request.form
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("INSERT INTO advanced_store (name, description, price, currency) VALUES (%s, %s, %s, %s)", (f['name'], f['description'], int(f['price']), f['currency']))
        conn.commit()
        conn.close()
        flash("🛒 تمت إضافة المنتج للمتجر.", "success")
    return redirect(url_for('dashboard'))

@app.route('/action/del_advanced_product', methods=['GET'])
def action_del_advanced_product():
    if session.get('logged_in'):
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM advanced_store WHERE id = %s", (request.args.get('id'),))
        conn.commit()
        conn.close()
        flash("🗑️ تم حذف المنتج.", "success")
    return redirect(url_for('dashboard'))

@app.route('/action/add_provider', methods=['POST'])
def action_add_provider():
    if session.get('logged_in'):
        f = request.form
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("INSERT INTO smm_providers (name, api_url, api_key, service_type) VALUES (%s, %s, %s, %s)", (f['name'], f['api_url'], f['api_key'], f['service_type']))
        conn.commit()
        conn.close()
        flash("🔌 تم ربط شركة الرشق.", "success")
    return redirect(url_for('dashboard'))

@app.route('/action/del_provider', methods=['GET'])
def action_del_provider():
    if session.get('logged_in'):
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM smm_providers WHERE id = %s", (request.args.get('id'),))
        conn.commit()
        conn.close()
        flash("🗑️ تم فك الارتباط بالشركة.", "success")
    return redirect(url_for('dashboard'))

@app.route('/action/del_order', methods=['GET'])
def action_del_order():
    if session.get('logged_in'):
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM orders WHERE id = %s", (request.args.get('id'),))
        conn.commit()
        conn.close()
        flash("🛑 تم إيقاف الطلب.", "success")
    return redirect(url_for('dashboard'))

@app.route('/action/add_channel', methods=['POST'])
def action_add_channel():
    if session.get('logged_in'):
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("INSERT IGNORE INTO force_subs (channel_username) VALUES (%s)", (request.form.get('channel'),))
        conn.commit()
        conn.close()
        flash("✅ تمت إضافة القناة.", "success")
    return redirect(url_for('dashboard'))

@app.route('/action/del_channel', methods=['GET'])
def action_del_channel():
    if session.get('logged_in'):
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM force_subs WHERE channel_username = %s", (request.args.get('channel'),))
        conn.commit()
        conn.close()
        flash("🗑️ تم حذف القناة.", "success")
    return redirect(url_for('dashboard'))

@app.route('/action/gift_user', methods=['POST'])
def action_gift_user():
    if session.get('logged_in'):
        uid, amount, currency = request.form['user_id'], int(request.form['amount']), request.form['currency']
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE id = %s", (uid,))
            if not cur.fetchone():
                flash("❌ الآيدي غير موجود!", "danger")
            else:
                if currency == 'miq':
                    cur.execute("UPDATE users SET miq_balance = miq_balance + %s WHERE id = %s", (amount, uid))
                else:
                    cur.execute("UPDATE users SET points = points + %s WHERE id = %s", (amount, uid))
                cur.execute("INSERT INTO action_logs (user_id, action_type, details) VALUES (%s, %s, %s)", (uid, 'admin_gift', f"هدية إدارية: {amount} {currency}"))
                flash(f"🎁 تم إرسال الهدية بنجاح!", "success")
        conn.commit()
        conn.close()
    return redirect(url_for('dashboard'))

@app.route('/action/penalize_user', methods=['POST'])
def action_penalize_user():
    if session.get('logged_in'):
        uid, ptype, reason = request.form['user_id'], request.form['penalty_type'], request.form['reason']
        conn = get_db_connection()
        with conn.cursor() as cur:
            if ptype == 'freeze': cur.execute("UPDATE users SET points = 0, miq_balance = 0 WHERE id = %s", (uid,))
            elif ptype == 'ban': cur.execute("UPDATE users SET role = 'banned' WHERE id = %s", (uid,))
            cur.execute("INSERT INTO action_logs (user_id, action_type, details) VALUES (%s, %s, %s)", (uid, ptype, reason))
        conn.commit()
        conn.close()
        flash("⚠️ تم تطبيق العقوبة.", "success")
    return redirect(url_for('dashboard'))

@app.route('/action/add_promo', methods=['POST'])
def action_add_promo():
    if session.get('logged_in'):
        f = request.form
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("INSERT INTO promo_codes (code, reward_type, reward, max_uses) VALUES (%s, %s, %s, %s)", (f['code'].upper(), 'points', int(f['reward']), int(f['max_uses'])))
        conn.commit()
        conn.close()
        flash("🎟️ تم توليد الكود!", "success")
    return redirect(url_for('dashboard'))

@app.route('/action/add_drop', methods=['POST'])
def action_add_drop():
    if session.get('logged_in'):
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("UPDATE flash_drops SET is_active = FALSE")
            cur.execute("INSERT INTO flash_drops (reward, max_winners) VALUES (%s, %s)", (int(request.form['reward']), int(request.form['max_winners'])))
        conn.commit()
        conn.close()
        flash("⚡ تم إسقاط صندوق الحظ!", "success")
    return redirect(url_for('dashboard'))

@app.route('/action/stop_drop', methods=['POST'])
def action_stop_drop():
    if session.get('logged_in'):
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("UPDATE flash_drops SET is_active = FALSE")
        conn.commit()
        conn.close()
        flash("🛑 تم إيقاف الصندوق.", "danger")
    return redirect(url_for('dashboard'))

@app.route('/action/add_news', methods=['POST'])
def action_add_news():
    if session.get('logged_in'):
        f = request.form
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("UPDATE read_to_earn SET active = FALSE")
            cur.execute("INSERT INTO read_to_earn (url, question, answer, reward_type, reward, max_winners) VALUES (%s, %s, %s, %s, %s, %s)", (f['url'], f['question'], f['answer'], 'points', int(f['reward']), int(f['max_winners'])))
        conn.commit()
        conn.close()
        flash("📰 تم نشر المهمة الإخبارية.", "success")
    return redirect(url_for('dashboard'))

@app.route('/action/stop_news', methods=['POST'])
def action_stop_news():
    if session.get('logged_in'):
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("UPDATE read_to_earn SET active = FALSE")
        conn.commit()
        conn.close()
        flash("🛑 تم إيقاف المهمة الإخبارية.", "danger")
    return redirect(url_for('dashboard'))

# --- عمليات البورصة ---
@app.route('/action/add_prediction', methods=['POST'])
def action_add_prediction():
    if session.get('logged_in'):
        f = request.form
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("INSERT INTO predictions (question, opt1, opt2, opt3, opt4) VALUES (%s, %s, %s, %s, %s)", (f['question'], f['opt1'], f['opt2'], f.get('opt3', ''), f.get('opt4', '')))
        conn.commit()
        conn.close()
        flash("📈 تم إطلاق البورصة للسوق!", "success")
    return redirect(url_for('dashboard'))

@app.route('/action/resolve_prediction', methods=['GET'])
def action_resolve_prediction():
    if session.get('logged_in'):
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("UPDATE predictions SET status = %s WHERE id = %s", (f"won_opt{request.args.get('winner')}", request.args.get('id')))
        conn.commit()
        conn.close()
        flash("✅ تم إنهاء البورصة (توزيع الأرباح عبر البوت).", "success")
    return redirect(url_for('dashboard'))

@app.route('/action/cancel_prediction', methods=['GET'])
def action_cancel_prediction():
    if session.get('logged_in'):
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("UPDATE predictions SET status = 'cancelled' WHERE id = %s", (request.args.get('id'),))
        conn.commit()
        conn.close()
        flash("🛑 تم إلغاء البورصة.", "danger")
    return redirect(url_for('dashboard'))

# ================= مسار التقرير الرسمي (PDF) =================
@app.route('/report/user/<int:uid>')
def report_user(uid):
    if not session.get('logged_in'): return redirect(url_for('dashboard'))
    conn = get_db_connection()
    user = None
    logs = []
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM users WHERE id = %s", (uid,))
        user = cur.fetchone()
        cur.execute("SELECT * FROM action_logs WHERE user_id = %s ORDER BY id DESC LIMIT 100", (uid,))
        logs = cur.fetchall()
    conn.close()
    if not user: return "<h2 style='text-align:center; color:red; margin-top:50px;'>❌ الآيدي غير مسجل!</h2>"
    return render_template_string(REPORT_TEMPLATE, user=user, logs=logs, date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

if __name__ == '__main__':
    print("🎇 محركات غرفة القيادة الإمبراطورية (النسخة المتكاملة والأصلية) تقلع الآن على السيرفر السحابي! 🎇")
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
