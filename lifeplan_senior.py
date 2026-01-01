import streamlit as st
import pandas as pd
import base64

# =========================
# 既定値（Excelの値に合わせて適宜変更してください）
# =========================
DEFAULT = {
    "h_now": 70, "h_die": 85,
    "w_now": 60, "w_die": 97,
    "start_savings": 3000.0,

    # 年収（年額・万円）
    "h_inc_now": 250.0, "h_g1": 0.0, "h_ch_age": 75, "h_inc_after": 180.0, "h_g2": 0.0,
    "w_inc_now": 500.0, "w_g1": 2.0, "w_ch_age": 65, "w_inc_after": 170.0, "w_g2": 0.0,

    # 一時収入（年額・万円）各3件
    "h_lump": [{"age": 76, "amt": 0.0}, {"age": 80, "amt": 0.0}, {"age": 85, "amt": 0.0}],
    "w_lump": [{"age": 65, "amt": 2000.0}, {"age": 70, "amt": 0.0}, {"age": 92, "amt": 6000.0}],

    # 生活費（画面は月額。既定値は年額÷12）
    "living": {
        "食費":            {"m": 90.0/12, "g": 2.0, "after_years": 10, "m2": 70.0/12, "g2": 3.0},
        "水道光熱費":      {"m": 45.0/12, "g": 2.0, "after_years": 10, "m2": 45.0/12, "g2": 3.0},
        "通信費":          {"m": 15.0/12, "g": 2.0, "after_years": 15, "m2": 10.0/12, "g2": 3.0},
        "交通費":          {"m": 10.0/12, "g": 2.0, "after_years": 10, "m2":  8.0/12, "g2": 3.0},
        "趣味・交際費":    {"m": 30.0/12, "g": 2.0, "after_years": 10, "m2": 10.0/12, "g2": 3.0},
        "医療費":          {"m": 20.0/12, "g": 2.0, "after_years": 15, "m2": 40.0/12, "g2": 3.0},
        "マンション管理費": {"m": 50.0/12, "g": 2.0, "after_years": 10, "m2": 80.0/12, "g2": 3.0},
        "その他":          {"m": 20.0/12, "g": 2.0, "after_years": 10, "m2": 30.0/12, "g2": 3.0},
    },

    # 介護費（月額・万円/月）
    "h_care_start": 85, "h_care_m": 40.0, "h_care_g": 3.0,
    "w_care_start": 90, "w_care_m": 50.0, "w_care_g": 3.0,

    # 一時支出（年額・万円）各3件
    "h_spend": [{"age": 75, "amt": 0.0}, {"age": 76, "amt": 0.0}, {"age": 85, "amt": 300.0}],
    "w_spend": [{"age": 60, "amt": 0.0}, {"age": 65, "amt": 0.0}, {"age": 90, "amt": 400.0}],
}

ITEMS = ["食費", "水道光熱費", "通信費", "交通費", "趣味・交際費", "医療費", "マンション管理費", "その他"]

# =========================
# ページ設定
# =========================
st.set_page_config(page_title="シニア向けライフプラン（ブラウザ版）", layout="wide")

# =========================
# CSS（黄色入力＋青い保存ボタンはShadow DOM回避で確実）
# =========================
st.markdown("""
<style>
div[data-baseweb="input"] > div,
div[data-baseweb="base-input"] > div,
div[data-baseweb="select"] > div {
    background-color:#fff2cc !important;
    border:2px solid #c9a400 !important;
    border-radius:10px !important;
}
.section-title { font-weight:900; font-size:1.12rem; margin:0.6rem 0 0.3rem 0; }
.subnote { color:#444; font-size:0.92rem; margin-top:-0.2rem; margin-bottom:0.3rem; }

/* 保存（確実に青）：HTMLリンクでダウンロード */
a.download-link {
    display:block;
    background:#1e88e5;
    color:white !important;
    text-align:center;
    font-weight:800;
    padding:0.9em;
    border-radius:14px;
    text-decoration:none;
    font-size:1.05rem;
}
a.download-link:hover { background:#1565c0; }
</style>
""", unsafe_allow_html=True)

st.title("シニア向けライフプランシミュレーション（ブラウザ版）")
st.caption("生活費8項目と介護費は月額（万円/月）。それ以外（年収・一時収入・一時支出・貯蓄残高）は年額（万円）。年次（1年刻み）で計算します。")

# =========================
# 共通入力（位置引数でもOK）
# =========================
def NI(label, key, min_value=None, max_value=None, value=None, step=None, **kwargs):
    params = {"label": label, "key": key}
    if min_value is not None: params["min_value"] = min_value
    if max_value is not None: params["max_value"] = max_value
    if value is not None: params["value"] = value
    if step is not None: params["step"] = step
    params.update(kwargs)
    return st.number_input(**params)

def build_lumps(prefix, title, defaults):
    st.markdown(f'<div class="section-title">■ {title}（最大3件）</div>', unsafe_allow_html=True)
    h1, h2, h3 = st.columns([1.0, 1.6, 0.6])
    h1.markdown("**何歳の時**")
    h2.markdown("**金額（万円）**")
    h3.markdown("**使用**")

    rows = []
    for i in range(1, 4):
        d = defaults[i-1]
        age0 = int(d["age"])
        amt0 = float(d["amt"])
        use0 = True if amt0 > 0 else False

        c1, c2, c3 = st.columns([1.0, 1.6, 0.6])
        with c1:
            age = NI("", f"{prefix}_age_{i}", 0, 120, age0, step=1, label_visibility="collapsed")
        with c2:
            amt = NI("", f"{prefix}_amt_{i}", 0.0, 999999.0, amt0, step=10.0, label_visibility="collapsed")
        with c3:
            use = st.checkbox("", value=use0, key=f"{prefix}_use_{i}", label_visibility="collapsed")

        rows.append((use, int(age), float(amt)))
    return rows

def lumps_to_map(lumps):
    mp = {}
    for use, age, amt in lumps:
        if use and age > 0 and amt > 0:
            mp[age] = mp.get(age, 0.0) + float(amt)
    return mp

# =========================
# 入力：年齢・貯蓄
# =========================
st.markdown('<div class="section-title">■ 年齢・貯蓄</div>', unsafe_allow_html=True)
c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 1.4])
with c1:
    h_now = NI("夫の現在年齢", "h_now", 0, 120, int(DEFAULT["h_now"]), step=1)
with c2:
    h_die = NI("夫の死亡年齢", "h_die", 0, 120, int(DEFAULT["h_die"]), step=1)
with c3:
    w_now = NI("妻の現在年齢", "w_now", 0, 120, int(DEFAULT["w_now"]), step=1)
with c4:
    w_die = NI("妻の死亡年齢", "w_die", 0, 120, int(DEFAULT["w_die"]), step=1)
with c5:
    start_savings = NI("夫婦合計の現在貯蓄額（万円）", "start_savings", 0.0, 999999.0, float(DEFAULT["start_savings"]), step=100.0)

if h_die < h_now:
    st.error("夫：死亡年齢は現在年齢以上にしてください。"); st.stop()
if w_die < w_now:
    st.error("妻：死亡年齢は現在年齢以上にしてください。"); st.stop()

start_age = min(int(h_now), int(w_now))
end_age = max(int(h_die), int(w_die))
ages = list(range(start_age, end_age + 1))

st.divider()

# =========================
# 入力：年収（ラベル短縮でズレ防止）
# =========================
st.markdown('<div class="section-title">■ 収入（手取り年収：年額・万円）</div>', unsafe_allow_html=True)
L, R = st.columns(2)

with L:
    st.markdown("**夫**")
    a = st.columns([1.2, 1.0, 1.2, 1.2, 1.0])
    with a[0]:
        h_inc_now = NI("現在年収(万円)", "h_inc_now", 0.0, 20000.0, float(DEFAULT["h_inc_now"]), step=10.0)
    with a[1]:
        h_g1 = NI("上昇率(％)", "h_g1", -100.0, 100.0, float(DEFAULT["h_g1"]), step=0.1)
    with a[2]:
        h_ch_age = NI("変更(何歳から)", "h_ch_age", 0, 120, int(DEFAULT["h_ch_age"]), step=1)
    with a[3]:
        h_inc_after = NI("変更後年収(万円)", "h_inc_after", 0.0, 20000.0, float(DEFAULT["h_inc_after"]), step=10.0)
    with a[4]:
        h_g2 = NI("上昇率(％)", "h_g2", -100.0, 100.0, float(DEFAULT["h_g2"]), step=0.1)

    h_lumps = build_lumps("h_lump", "夫の一時収入（年額・万円）", DEFAULT["h_lump"])

with R:
    st.markdown("**妻**")
    b = st.columns([1.2, 1.0, 1.2, 1.2, 1.0])
    with b[0]:
        w_inc_now = NI("現在年収(万円)", "w_inc_now", 0.0, 20000.0, float(DEFAULT["w_inc_now"]), step=10.0)
    with b[1]:
        w_g1 = NI("上昇率(％)", "w_g1", -100.0, 100.0, float(DEFAULT["w_g1"]), step=0.1)
    with b[2]:
        w_ch_age = NI("変更(何歳から)", "w_ch_age", 0, 120, int(DEFAULT["w_ch_age"]), step=1)
    with b[3]:
        w_inc_after = NI("変更後年収(万円)", "w_inc_after", 0.0, 20000.0, float(DEFAULT["w_inc_after"]), step=10.0)
    with b[4]:
        w_g2 = NI("上昇率(％)", "w_g2", -100.0, 100.0, float(DEFAULT["w_g2"]), step=0.1)

    w_lumps = build_lumps("w_lump", "妻の一時収入（年額・万円）", DEFAULT["w_lump"])

st.divider()

# =========================
# 入力：生活費（8項目：月額）※ここに「合計行」だけ追加
# =========================
st.markdown('<div class="section-title">■ 生活費（8項目：月額・万円/月）</div>', unsafe_allow_html=True)
st.markdown('<div class="subnote">変更条件は「何年後から」。上昇率はすべて「上昇率(％)」表記に統一。</div>', unsafe_allow_html=True)

living_params = {}

# ★追加：合計（現在/月・変更後/月）を計算するだけ。入力欄の配置は一切変えない。
living_sum_now_m = 0.0
living_sum_after_m = 0.0

for name in ITEMS:
    d = DEFAULT["living"][name]
    st.markdown(f"**{name}**")
    cols = st.columns([1.1, 0.9, 1.0, 1.1, 0.9])
    with cols[0]:
        m = NI("月額(万円/月)", f"lv_{name}_m", 0.0, 99999.0, float(d["m"]), step=0.5)
    with cols[1]:
        g = NI("上昇率(％)", f"lv_{name}_g", -100.0, 100.0, float(d["g"]), step=0.1)
    with cols[2]:
        after_years = NI("変更(何年後から)", f"lv_{name}_after", 0, 60, int(d["after_years"]), step=1)
    with cols[3]:
        m2 = NI("変更後月額(万円/月)", f"lv_{name}_m2", 0.0, 99999.0, float(d["m2"]), step=0.5)
    with cols[4]:
        g2 = NI("上昇率(％)", f"lv_{name}_g2", -100.0, 100.0, float(d["g2"]), step=0.1)

    living_params[name] = dict(m=m, g=g, after_years=after_years, m2=m2, g2=g2)

    # ★追加：合計用に足し算するだけ（見た目は変えない）
    living_sum_now_m += float(m)
    living_sum_after_m += float(m2)

    st.markdown("---")

# ★追加：生活費ブロックの一番下に合計を表示（入力欄の形はそのまま）
st.markdown("### 生活費 合計（月額）")
s1, s2 = st.columns(2)
with s1:
    st.metric("現在 合計（万円/月）", f"{living_sum_now_m:,.1f}")
with s2:
    st.metric("変更後 合計（万円/月）", f"{living_sum_after_m:,.1f}")

st.divider()

# =========================
# 入力：介護費（月額）
# =========================
st.markdown('<div class="section-title">■ 介護費用（月額・万円/月）</div>', unsafe_allow_html=True)
c1, c2 = st.columns(2)
with c1:
    st.markdown("**夫**")
    h_care_start = NI("何歳から", "h_care_start", 0, 120, int(DEFAULT["h_care_start"]), step=1)
    h_care_m = NI("月額(万円/月)", "h_care_m", 0.0, 99999.0, float(DEFAULT["h_care_m"]), step=1.0)
    h_care_g = NI("上昇率(％)", "h_care_g", -100.0, 100.0, float(DEFAULT["h_care_g"]), step=0.1)
with c2:
    st.markdown("**妻**")
    w_care_start = NI("何歳から", "w_care_start", 0, 120, int(DEFAULT["w_care_start"]), step=1)
    w_care_m = NI("月額(万円/月)", "w_care_m", 0.0, 99999.0, float(DEFAULT["w_care_m"]), step=1.0)
    w_care_g = NI("上昇率(％)", "w_care_g", -100.0, 100.0, float(DEFAULT["w_care_g"]), step=0.1)

st.divider()

# =========================
# 入力：一時支出（年額）
# =========================
L2, R2 = st.columns(2)
with L2:
    h_spends = build_lumps("h_spend", "夫の一時支出（年額・万円）", DEFAULT["h_spend"])
with R2:
    w_spends = build_lumps("w_spend", "妻の一時支出（年額・万円）", DEFAULT["w_spend"])

# =========================
# 年次計算関数
# =========================
def income_for_person(age, now_age, die_age, inc1, g1, ch_age, inc2, g2, lump_map):
    if age < now_age or age > die_age:
        return 0.0
    if ch_age and age >= int(ch_age):
        years = age - int(ch_age)
        base = float(inc2) * ((1.0 + float(g2)/100.0) ** years)
    else:
        years = age - int(now_age)
        base = float(inc1) * ((1.0 + float(g1)/100.0) ** years)
    base += float(lump_map.get(age, 0.0))
    return base

def living_item_annual(age, start_age, m, g, after_years, m2, g2):
    if age < start_age:
        return 0.0
    change_age = int(start_age) + int(after_years) if int(after_years) > 0 else None
    if change_age is not None and age >= change_age:
        years = age - change_age
        mm = float(m2) * ((1.0 + float(g2)/100.0) ** years)
    else:
        years = age - int(start_age)
        mm = float(m) * ((1.0 + float(g)/100.0) ** years)
    return float(mm) * 12.0

def care_annual(age, now_age, die_age, start_age, monthly, g):
    if age < now_age or age > die_age:
        return 0.0
    if start_age and age >= int(start_age):
        years = age - int(start_age)
        mm = float(monthly) * ((1.0 + float(g)/100.0) ** years)
        return float(mm) * 12.0
    return 0.0

# =========================
# 実行（中央・色付き）
# =========================
st.markdown('<div class="section-title">■ 実行</div>', unsafe_allow_html=True)
bL, bC, bR = st.columns([1, 2, 1])
with bC:
    calc = st.button("計算", type="primary", use_container_width=True)

if "result_df" not in st.session_state:
    st.session_state["result_df"] = None

if calc:
    h_lump_map = lumps_to_map(h_lumps)
    w_lump_map = lumps_to_map(w_lumps)
    h_spend_map = lumps_to_map(h_spends)
    w_spend_map = lumps_to_map(w_spends)

    bal = float(start_savings)
    rows = []

    for age in ages:
        h_alive = int(h_now) <= age <= int(h_die)
        w_alive = int(w_now) <= age <= int(w_die)

        inc_h = income_for_person(age, int(h_now), int(h_die), h_inc_now, h_g1, h_ch_age, h_inc_after, h_g2, h_lump_map) if h_alive else 0.0
        inc_w = income_for_person(age, int(w_now), int(w_die), w_inc_now, w_g1, w_ch_age, w_inc_after, w_g2, w_lump_map) if w_alive else 0.0
        income_total = inc_h + inc_w

        living_total = 0.0
        for nm, p in living_params.items():
            living_total += living_item_annual(age, start_age, p["m"], p["g"], p["after_years"], p["m2"], p["g2"])

        care_total = 0.0
        care_total += care_annual(age, int(h_now), int(h_die), h_care_start, h_care_m, h_care_g) if h_alive else 0.0
        care_total += care_annual(age, int(w_now), int(w_die), w_care_start, w_care_m, w_care_g) if w_alive else 0.0

        lump_spend = (float(h_spend_map.get(age, 0.0)) if h_alive else 0.0) + (float(w_spend_map.get(age, 0.0)) if w_alive else 0.0)

        expense_total = living_total + care_total + lump_spend
        cashflow = income_total - expense_total
        bal += cashflow

        rows.append({
            "年齢": age,
            "世帯_年収合計(万円)": round(income_total, 1),
            "生活費合計(年額・万円)": round(living_total, 1),
            "介護費合計(年額・万円)": round(care_total, 1),
            "一時支出合計(万円)": round(lump_spend, 1),
            "年間現金収支(万円)": round(cashflow, 1),
            "貯蓄残高(万円)": round(bal, 1),
        })

    st.session_state["result_df"] = pd.DataFrame(rows)

# =========================
# 出力：表＋グラフ2つ＋保存（青）
# =========================
df = st.session_state.get("result_df", None)
if df is not None:
    st.success("計算できました。")

    left, right = st.columns([1.55, 1.0])
    with left:
        st.subheader("ライフプラン表（年次）")
        st.dataframe(df, use_container_width=True, hide_index=True)
    with right:
        st.subheader("グラフ① 年間現金収支（万円）")
        st.line_chart(df.set_index("年齢")[["年間現金収支(万円)"]])
        st.subheader("グラフ② 貯蓄残高（万円）")
        st.line_chart(df.set_index("年齢")[["貯蓄残高(万円)"]])

    csv = df.to_csv(index=False, encoding="utf-8-sig")
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a class="download-link" href="data:text/csv;base64,{b64}" download="lifeplan_result.csv">保存</a>'

    l, c, r = st.columns([1, 2, 1])
    with c:
        st.markdown(href, unsafe_allow_html=True)
else:
    st.info("まだ計算していません。中央の「計算」ボタンを押してください。")
