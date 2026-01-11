
import streamlit as st
import pandas as pd
import html
import altair as alt
from io import BytesIO
import os
import urllib.parse

import matplotlib.pyplot as plt
import matplotlib
from matplotlib import font_manager

from typing import List, Tuple, Optional

# ====== reportlab（PDF生成） ======
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont


# =========================
# ★あなた指定のデフォルト値
# =========================
DEFAULT = {
    # 年齢・貯蓄
    "h_now": 60, "h_die": 93,
    "w_now": 57, "w_die": 96,
    "start_savings": 1500.0,

    # 収入（年額・万円）
    "h_inc_now": 500.0, "h_g1": 2.0, "h_ch_age": 65, "h_inc_after": 180.0, "h_g2": 1.0,
    "w_inc_now": 300.0, "w_g1": 2.0, "w_ch_age": 65, "w_inc_after": 160.0, "w_g2": 1.0,

    # 一時収入（年額・万円）各3件
    "h_lump": [
        {"age": 65, "amt": 1500.0, "is_checked": True},
        {"age": 70, "amt": 200.0,  "is_checked": True},
        {"age": 80, "amt": 0.0,    "is_checked": False},
    ],
    "w_lump": [
        {"age": 65, "amt": 700.0,  "is_checked": True},
        {"age": 72, "amt": 300.0,  "is_checked": True},
        {"age": 80, "amt": 0.0,    "is_checked": False},
    ],

    # 生活費（画面は月額：万円/月）
    "living": {
        "食費": {"m": 8.5, "g": 2.0, "after_years": 8,  "m2": 5.5, "g2": 2.5},
        "水道光熱費": {"m": 3.5, "g": 2.0, "after_years": 8,  "m2": 2.0, "g2": 2.5},
        "通信費": {"m": 2.0, "g": 2.0, "after_years": 8,  "m2": 0.5, "g2": 2.5},
        "交通費": {"m": 2.0, "g": 2.0, "after_years": 8,  "m2": 0.8, "g2": 2.5},
        "趣味・交際費": {"m": 3.0, "g": 2.0, "after_years": 8,  "m2": 0.8, "g2": 2.5},
        "医療費": {"m": 1.8, "g": 2.0, "after_years": 10, "m2": 3.0, "g2": 3.0},
        "住宅の固定資産税・管理費等": {"m": 3.0, "g": 2.0, "after_years": 10, "m2": 4.0, "g2": 2.5},
        "その他": {"m": 6.0, "g": 2.0, "after_years": 10, "m2": 3.0, "g2": 2.5},
    },

    # ★単身世帯になったときの生活費割合（%）
    "single_ratio_pct": 75,

    # 介護費（月額・万円/月）
    "h_care_start": 88, "h_care_m": 30.0, "h_care_g": 2.5,
    "w_care_start": 90, "w_care_m": 35.0, "w_care_g": 2.5,

    # 一時支出（年額・万円）各3件（※夫婦ともすべてチェック）
    "h_spend": [
        {"age": 65, "amt": 200.0, "is_checked": True},
        {"age": 70, "amt": 150.0, "is_checked": True},
        {"age": 88, "amt": 100.0, "is_checked": True},
    ],
    "w_spend": [
        {"age": 60, "amt": 50.0,  "is_checked": True},
        {"age": 65, "amt": 100.0, "is_checked": True},
        {"age": 90, "amt": 100.0, "is_checked": True},
    ],
}

ITEMS = ["食費", "水道光熱費", "通信費", "交通費", "趣味・交際費", "医療費", "住宅の固定資産税・管理費等", "その他"]
APP_TITLE = "シニア夫婦のライフプラン・シミュレーション"

# =========================
# 画像設定（タイトル横）
# =========================
TITLE_IMAGE_FILENAME = "senior_couple.png"

# =========================
# ページ設定
# =========================
st.set_page_config(page_title=APP_TITLE, layout="wide")


# =========================
# CSS（入力色＋表固定＋タブ強調）
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

/* タブを大きく＆目立たせる */
div[data-baseweb="tab-list"] { gap: 10px !important; }
button[data-baseweb="tab"] {
    font-size: 1.35rem !important;
    font-weight: 900 !important;
    padding: 0.80rem 1.5rem !important;
    border-radius: 14px !important;
    background: #f3f4f6 !important;
    color: #111827 !important;
    border: 2px solid #d1d5db !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    background: #1e88e5 !important;
    color: white !important;
    border: 2px solid #1565c0 !important;
    box-shadow: 0 6px 16px rgba(30,136,229,0.25) !important;
    transform: translateY(-1px);
}

/* 表本体 */
.table-wrap {
    overflow:auto;
    border:1px solid #ddd;
    border-radius:10px;
    max-height: 620px;
}
.life-table {
    border-collapse: separate;
    border-spacing: 0;
    width: max-content;
    min-width: 100%;
    font-size: 14px;
}
.life-table th, .life-table td{
    border-bottom: 1px solid #e6e6e6;
    border-right: 1px solid #f0f0f0;
    padding: 6px 10px;
    text-align: center;
    white-space: nowrap;
    background: white;
    position: relative;
}
.life-table thead th{
    position: sticky;
    top: 0;
    z-index: 3;
    background: #fafafa;
    font-weight: 800;
}
.life-table .sticky-col{
    position: sticky;
    left: 0;
    z-index: 4;
    background: #ffffff;
    text-align: left;
    font-weight: 800;
    border-right: 2px solid #d0d0d0;
}
.life-table .sticky-col::after{
    content:"";
    position:absolute;
    right:-6px; top:0;
    width:6px; height:100%;
    background: linear-gradient(to right, rgba(0,0,0,0.08), rgba(0,0,0,0));
}
:root{
  --thead-h: 36px;
  --row-h: 32px;
}
.life-table tr.sticky-row-1 td{
  position: sticky;
  top: var(--thead-h);
  z-index: 2;
  background: #ffffff;
}
.life-table tr.sticky-row-2 td{
  position: sticky;
  top: calc(var(--thead-h) + var(--row-h));
  z-index: 2;
  background: #ffffff;
}
.life-table tr.sticky-row-1 td.sticky-col,
.life-table tr.sticky-row-2 td.sticky-col{
  z-index: 6;
  background: #ffffff;
  left: 0;
}
.life-table thead th.sticky-col{
  left: 0;
  z-index: 8;
  background: #fafafa;
}

/* 質問欄（text_area）を目立たせる */
div[data-baseweb="textarea"] > div{
  background-color:#ffe6ef !important;
  border:2px solid #ff5a8a !important;
  border-radius:12px !important;
}
div[data-baseweb="textarea"] textarea{
  background-color:#ffe6ef !important;
}

/* ★ここが今回の本命：3行だけ確実に紺色 */
.ppk-poem .ppk-line{
  color:#0b1f4b !important;
  font-weight:900 !important;
}
</style>
""", unsafe_allow_html=True)


# =========================
# 「ざっくりつかむ」→ タイトルの上（赤・少し大きめ）
# =========================
st.markdown(
    """
    <div style="color:#d32f2f; font-size:1.55rem; font-weight:900; margin:0.15rem 0 0.10rem 0;">
      ざっくりつかむ
    </div>
    """,
    unsafe_allow_html=True
)

# =========================
# タイトル＋画像（バランス配置）
# =========================
t1, t2 = st.columns([4.2, 1.3], vertical_alignment="center")
with t1:
    st.title(APP_TITLE)

    # ★タイトル直下（3行＋説明）
    st.markdown(
        """
        <div style="margin-top:-0.4rem; margin-bottom:0.45rem;">

          <!-- ★3行：classで指定。CSSで紺色が「必ず」当たります -->
          <div class="ppk-poem" style="font-size:1.10rem; line-height:2.0; margin-top:0.15rem;">
            <div class="ppk-line" style="margin-left: 8.2rem;">ピンピンコロリと　いきたいが</div>
            <div class="ppk-line" style="margin-left:10.2rem;">そうは問屋が　おろさない</div>
            <div class="ppk-line" style="margin-left:12.2rem;">さてさてどうなる　この人生</div>
          </div>

          <div style="margin-top:0.55rem; color:#555; font-size:0.93rem; line-height:1.75;">
            ※まずは試しに「年齢」と「貯蓄額」だけ入れて、下の
            <span style="font-size:1.10rem; font-weight:900; color:#333;">【計算】</span>
            をポン！数字を変えて、またポン！ それだけ。結果を見て、AIのコメントをチェック。（目安としてご利用ください）　シニアは現金が重要。すべて現金ベースで計算します。
          </div>

        </div>
        """,
        unsafe_allow_html=True
    )

    st.caption("生活費8項目と介護費は月額（万円/月）。それ以外（年収・一時収入・一時支出）は年額（万円）。年次（1年刻み）で計算します。※シニアが作りました。")

with t2:
    img_path = os.path.join(os.path.dirname(__file__), TITLE_IMAGE_FILENAME)
    if os.path.exists(img_path):
        st.image(img_path, use_container_width=True)
    else:
        st.caption(f"※画像 {TITLE_IMAGE_FILENAME} が見つかりません（このpyと同じ場所に置いてください）")


# =========================
# matplotlib 日本語フォント（□対策）
# =========================
def set_japanese_font_for_matplotlib():
    candidates = [
        "Yu Gothic", "Yu Gothic UI", "Meiryo", "MS Gothic", "MS PGothic",
        "Hiragino Sans", "Noto Sans CJK JP", "IPAexGothic", "TakaoGothic"
    ]
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in candidates:
        if name in available:
            matplotlib.rcParams["font.family"] = name
            matplotlib.rcParams["axes.unicode_minus"] = False
            return
    matplotlib.rcParams["axes.unicode_minus"] = False


# =========================
# 入力（数値：型統一）
# =========================
def NI_INT(label, key, min_v, max_v, value, step=1, **kwargs):
    return st.number_input(
        label, key=key,
        min_value=int(min_v), max_value=int(max_v),
        value=int(value), step=int(step),
        **kwargs
    )

def NI_FLOAT(label, key, min_v, max_v, value, step=0.1, **kwargs):
    return st.number_input(
        label, key=key,
        min_value=float(min_v), max_value=float(max_v),
        value=float(value), step=float(step),
        format="%.1f",
        **kwargs
    )


# =========================
# 一時収入/支出 入力（最大3件）
# =========================
def build_lumps(prefix, title, defaults, note_text=None):
    st.markdown(f'<div class="section-title">■ {title}（最大3件）</div>', unsafe_allow_html=True)

    h1, h2, h3 = st.columns([1.0, 1.6, 0.6])
    h1.markdown("**何歳の時**")
    h2.markdown("**金額（万円）**")
    h3.markdown("**使用**")

    rows = []
    for i in range(1, 4):
        d = defaults[i-1]
        age0 = int(d.get("age", 0))
        amt0 = float(d.get("amt", 0.0))
        use0 = bool(d.get("is_checked", (amt0 > 0)))

        c1, c2, c3 = st.columns([1.0, 1.6, 0.6])
        with c1:
            age = NI_INT("", f"{prefix}_age_{i}", 0, 120, age0, 1, label_visibility="collapsed")
        with c2:
            amt = NI_FLOAT("", f"{prefix}_amt_{i}", 0.0, 999999.0, amt0, 0.1, label_visibility="collapsed")
        with c3:
            use = st.checkbox("", value=use0, key=f"{prefix}_use_{i}", label_visibility="collapsed")

        rows.append((bool(use), int(age), float(amt)))

    if note_text:
        st.markdown(
            '<div style="font-size:0.80rem;color:#666;margin-top:-0.10rem;">'
            + html.escape(note_text).replace("\n", "<br>")
            + '</div>',
            unsafe_allow_html=True
        )
    return rows

def lumps_to_map(lumps):
    mp = {}
    for use, age, amt in lumps:
        if use and age > 0 and amt > 0:
            mp[age] = mp.get(age, 0.0) + float(amt)
    return mp


# =========================
# 単身期開始（年目）
# =========================
def get_single_start_year_after(h_now, h_die, w_now, w_die):
    h_death_y = (h_die - h_now + 1) if h_die >= h_now else None
    w_death_y = (w_die - w_now + 1) if w_die >= w_now else None
    ys = [y for y in [h_death_y, w_death_y] if y is not None]
    if not ys:
        return None
    return min(ys) + 1


# =========================
# 年次計算（単身期：夫婦期最終年の生活費×割合）
# =========================
def calc_lifeplan(inputs: dict):
    h_now = int(inputs["h_now"]); h_die = int(inputs["h_die"])
    w_now = int(inputs["w_now"]); w_die = int(inputs["w_die"])
    start_savings = float(inputs["start_savings"])

    years_len = max(h_die - h_now, w_die - w_now) + 1
    year_labels = [str(i + 1) for i in range(years_len)]

    living_params = inputs["living_params"]
    h_lump_map = inputs["h_lump_map"]
    w_lump_map = inputs["w_lump_map"]
    h_spend_map = inputs["h_spend_map"]
    w_spend_map = inputs["w_spend_map"]

    single_ratio_pct = float(inputs.get("single_ratio_pct", 100.0))
    single_ratio = max(min(single_ratio_pct / 100.0, 2.0), 0.0)
    single_start_y = get_single_start_year_after(h_now, h_die, w_now, w_die)

    def income_base_by_age(age, now_age, die_age, inc1, g1, ch_age, inc2, g2):
        if age < now_age or age > die_age:
            return 0.0
        if ch_age and age >= int(ch_age):
            yy = age - int(ch_age)
            return float(inc2) * ((1.0 + float(g2)/100.0) ** yy)
        yy = age - int(now_age)
        return float(inc1) * ((1.0 + float(g1)/100.0) ** yy)

    def living_monthly_by_t(t, p):
        t = int(t)
        after = int(p["after_years"])
        if after > 0 and t >= after:
            dt = t - after
            mm = float(p["m2"]) * ((1.0 + float(p["g2"])/100.0) ** dt)
        else:
            mm = float(p["m"]) * ((1.0 + float(p["g"])/100.0) ** t)
        return float(mm)

    def care_annual_by_age(age, now_age, die_age, start_age, monthly, g):
        if age < now_age or age > die_age:
            return 0.0
        if start_age and age >= int(start_age):
            yy = age - int(start_age)
            mm = float(monthly) * ((1.0 + float(g)/100.0) ** yy)
            return round(float(mm) * 12.0, 1)
        return 0.0

    couple_last_t = None
    if single_start_y is not None and 1 <= int(single_start_y) <= years_len:
        couple_last_t = int(single_start_y) - 2

    couple_last_monthly = {}
    if couple_last_t is not None and couple_last_t >= 0:
        for nm in ITEMS:
            couple_last_monthly[nm] = living_monthly_by_t(couple_last_t, living_params[nm])

    def living_item_annual_by_t(t, p, name):
        t = int(t)
        year_idx = t + 1
        if single_start_y is not None and year_idx >= int(single_start_y) and couple_last_t is not None and couple_last_t >= 0:
            base_mm = float(couple_last_monthly.get(name, living_monthly_by_t(couple_last_t, p)))
            dt = year_idx - int(single_start_y)
            mm = base_mm * single_ratio * ((1.0 + float(p["g2"])/100.0) ** dt)
            return round(float(mm) * 12.0, 1)

        mm = living_monthly_by_t(t, p)
        return round(float(mm) * 12.0, 1)

    rows_table, idx_table = [], []
    blank_counter = 0
    def add_blank():
        nonlocal blank_counter
        blank_counter += 1
        idx_table.append(f"__blank{blank_counter}__")
        rows_table.append([""] * years_len)

    h_age_row, w_age_row = [], []
    for t in range(years_len):
        ah, aw = h_now + t, w_now + t
        h_age_row.append(ah if ah <= h_die else "")
        w_age_row.append(aw if aw <= w_die else "")
    idx_table += ["夫年齢", "妻年齢"]
    rows_table += [h_age_row, w_age_row]

    single_row = [""] * years_len
    if single_start_y is not None and 1 <= int(single_start_y) <= years_len:
        single_row[int(single_start_y) - 1] = "←ここから単身期"
    idx_table.append("単身期開始")
    rows_table.append(single_row)

    h_inc_row, w_inc_row = [], []
    h_lump_row, w_lump_row = [], []
    income_total_row = []
    for t in range(years_len):
        ah, aw = h_now + t, w_now + t
        h_alive = (ah <= h_die)
        w_alive = (aw <= w_die)

        h_base = income_base_by_age(
            ah, h_now, h_die,
            inputs["h_inc_now"], inputs["h_g1"], inputs["h_ch_age"],
            inputs["h_inc_after"], inputs["h_g2"]
        ) if h_alive else 0.0

        w_base = income_base_by_age(
            aw, w_now, w_die,
            inputs["w_inc_now"], inputs["w_g1"], inputs["w_ch_age"],
            inputs["w_inc_after"], inputs["w_g2"]
        ) if w_alive else 0.0

        hl = float(h_lump_map.get(ah, 0.0)) if h_alive else 0.0
        wl = float(w_lump_map.get(aw, 0.0)) if w_alive else 0.0

        h_inc_row.append(round(h_base, 1))
        w_inc_row.append(round(w_base, 1))
        h_lump_row.append(round(hl, 1))
        w_lump_row.append(round(wl, 1))
        income_total_row.append(round(h_base + w_base + hl + wl, 1))

    idx_table += ["夫年収(手取り)", "妻年収(手取り)", "一時収入 夫", "一時収入 妻", "収入合計"]
    rows_table += [h_inc_row, w_inc_row, h_lump_row, w_lump_row, income_total_row]

    add_blank()

    living_item_rows = {nm: [] for nm in ITEMS}
    for t in range(years_len):
        for nm in ITEMS:
            living_item_rows[nm].append(float(living_item_annual_by_t(t, living_params[nm], nm)))

    for nm in ITEMS:
        idx_table.append(nm)
        rows_table.append(living_item_rows[nm])

    care_h_row, care_w_row = [], []
    for t in range(years_len):
        ah, aw = h_now + t, w_now + t
        care_h = care_annual_by_age(ah, h_now, h_die, inputs["h_care_start"], inputs["h_care_m"], inputs["h_care_g"]) if ah <= h_die else 0.0
        care_w = care_annual_by_age(aw, w_now, w_die, inputs["w_care_start"], inputs["w_care_m"], inputs["w_care_g"]) if aw <= w_die else 0.0
        care_h_row.append(round(float(care_h), 1))
        care_w_row.append(round(float(care_w), 1))
    idx_table += ["介護費 夫", "介護費 妻"]
    rows_table += [care_h_row, care_w_row]

    spend_h_row, spend_w_row = [], []
    for t in range(years_len):
        ah, aw = h_now + t, w_now + t
        spend_h_row.append(round(float(h_spend_map.get(ah, 0.0)) if ah <= h_die else 0.0, 1))
        spend_w_row.append(round(float(w_spend_map.get(aw, 0.0)) if aw <= w_die else 0.0, 1))
    idx_table += ["一時支出 夫", "一時支出 妻"]
    rows_table += [spend_h_row, spend_w_row]

    expense_total_row, cashflow_row, balance_row = [], [], []
    bal = start_savings
    for t in range(years_len):
        living_total = sum(living_item_rows[nm][t] for nm in ITEMS)
        care_total = care_h_row[t] + care_w_row[t]
        spend_total = spend_h_row[t] + spend_w_row[t]
        expense_total = living_total + care_total + spend_total

        cashflow = income_total_row[t] - expense_total
        bal += cashflow

        expense_total_row.append(round(float(expense_total), 1))
        cashflow_row.append(round(float(cashflow), 1))
        balance_row.append(round(float(bal), 1))

    idx_table.append("支出合計")
    rows_table.append(expense_total_row)

    add_blank()

    idx_table += ["現金収支", "貯蓄残高"]
    rows_table += [cashflow_row, balance_row]

    df_table = pd.DataFrame(rows_table, index=idx_table, columns=year_labels)

    df_long = pd.DataFrame({
        "年目": list(range(1, years_len + 1)),
        "年間現金収支(万円)": cashflow_row,
        "貯蓄残高(万円)": balance_row,
    })
    return df_long, df_table


def df_view_for_display(df_table: pd.DataFrame) -> pd.DataFrame:
    df_view = df_table.reset_index().rename(columns={"index": "年目"})
    df_view = df_view.fillna("")
    df_view["年目"] = df_view["年目"].astype(str).apply(lambda x: "" if x.startswith("__blank") else x)

    def add_unit(label):
        if label in ["夫年齢", "妻年齢", "単身期開始"] or label == "":
            return label
        if "（万円）" in label:
            return label
        return f"{label}（万円）"

    df_view["年目"] = df_view["年目"].apply(add_unit)
    return df_view


def df_to_sticky_html(df_view: pd.DataFrame) -> str:
    cols = list(df_view.columns)

    thead = "<thead><tr>"
    for j, c in enumerate(cols):
        cls = "sticky-col" if j == 0 else ""
        thead += f'<th class="{cls}">{html.escape(str(c))}</th>'
    thead += "</tr></thead>"

    tbody = "<tbody>"
    for _, row in df_view.iterrows():
        label = str(row.iloc[0])

        row_class = ""
        if label == "夫年齢":
            row_class = "sticky-row-1"
        elif label == "妻年齢":
            row_class = "sticky-row-2"

        bg = ""
        fg = ""
        fw = ""
        if str(label).startswith("収入合計"):
            bg = "background:#00b0f0;"
            fg = "color:white;"
            fw = "font-weight:900;"
        elif str(label).startswith("支出合計"):
            bg = "background:#ff0000;"
            fg = "color:white;"
            fw = "font-weight:900;"
        elif str(label).startswith("貯蓄残高"):
            bg = "background:#92d050;"
            fg = "color:black;"
            fw = "font-weight:900;"
        elif str(label).startswith("単身期開始"):
            bg = "background:#fff4c2;"
            fg = "color:#111827;"
            fw = "font-weight:900;"

        tbody += f'<tr class="{row_class}">'
        for j, c in enumerate(cols):
            v = row[c]
            cls = "sticky-col" if j == 0 else ""
            style = f"{bg}{fg}{fw}"

            if j == 0:
                tbody += f'<td class="{cls}" style="{style}">{html.escape(str(v))}</td>'
            else:
                if v == "" or v is None:
                    s = ""
                else:
                    try:
                        if label in ["夫年齢", "妻年齢"]:
                            s = f"{int(float(v))}"
                        else:
                            if label.startswith("単身期開始"):
                                s = html.escape(str(v))
                            else:
                                s = f"{float(v):.1f}"
                    except:
                        s = html.escape(str(v))
                tbody += f'<td style="{style}">{s}</td>'
        tbody += "</tr>"
    tbody += "</tbody>"

    return f'<div class="table-wrap"><table class="life-table">{thead}{tbody}</table></div>'


def build_inputs_table(inputs: dict) -> pd.DataFrame:
    rows = []
    rows += [
        ("年齢・貯蓄", "夫の現在年齢", f"{inputs['h_now']} 歳"),
        ("年齢・貯蓄", "夫の死亡年齢", f"{inputs['h_die']} 歳"),
        ("年齢・貯蓄", "妻の現在年齢", f"{inputs['w_now']} 歳"),
        ("年齢・貯蓄", "妻の死亡年齢", f"{inputs['w_die']} 歳"),
        ("年齢・貯蓄", "夫婦合計の現在貯蓄額", f"{inputs['start_savings']:.1f} 万円"),
    ]

    rows += [
        ("収入（夫）", "現在年収（年額）", f"{inputs['h_inc_now']:.1f} 万円"),
        ("収入（夫）", "上昇率", f"{inputs['h_g1']:.1f} ％"),
        ("収入（夫）", "変更（何歳から）", f"{inputs['h_ch_age']} 歳"),
        ("収入（夫）", "変更後年収（年額）", f"{inputs['h_inc_after']:.1f} 万円"),
        ("収入（夫）", "変更後上昇率", f"{inputs['h_g2']:.1f} ％"),
    ]

    rows += [
        ("収入（妻）", "現在年収（年額）", f"{inputs['w_inc_now']:.1f} 万円"),
        ("収入（妻）", "上昇率", f"{inputs['w_g1']:.1f} ％"),
        ("収入（妻）", "変更（何歳から）", f"{inputs['w_ch_age']} 歳"),
        ("収入（妻）", "変更後年収（年額）", f"{inputs['w_inc_after']:.1f} 万円"),
        ("収入（妻）", "変更後上昇率", f"{inputs['w_g2']:.1f} ％"),
    ]

    for who, lumps in [("一時収入（夫）", inputs["h_lumps"]), ("一時収入（妻）", inputs["w_lumps"])]:
        for i, (use, age, amt) in enumerate(lumps, start=1):
            rows.append((who, f"{i}件目 使用", "はい" if use else "いいえ"))
            rows.append((who, f"{i}件目 年齢", f"{age} 歳"))
            rows.append((who, f"{i}件目 金額（年額）", f"{amt:.1f} 万円"))

    for nm, p in inputs["living_params"].items():
        rows.append(("生活費", f"{nm} 月額", f"{p['m']:.1f} 万円/月"))
        rows.append(("生活費", f"{nm} 上昇率", f"{p['g']:.1f} ％"))
        rows.append(("生活費", f"{nm} 変更（何年後から）", f"{p['after_years']} 年後"))
        rows.append(("生活費", f"{nm} 変更後月額", f"{p['m2']:.1f} 万円/月"))
        rows.append(("生活費", f"{nm} 変更後上昇率", f"{p['g2']:.1f} ％"))

        if nm == "その他":
            rows.append(("生活費", "単身世帯になったときの生活費の割合(％)", f"{int(inputs.get('single_ratio_pct', 100))} ％"))

    rows += [
        ("介護費（夫）", "何歳から", f"{inputs['h_care_start']} 歳"),
        ("介護費（夫）", "月額", f"{inputs['h_care_m']:.1f} 万円/月"),
        ("介護費（夫）", "上昇率", f"{inputs['h_care_g']:.1f} ％"),
        ("介護費（妻）", "何歳から", f"{inputs['w_care_start']} 歳"),
        ("介護費（妻）", "月額", f"{inputs['w_care_m']:.1f} 万円/月"),
        ("介護費（妻）", "上昇率", f"{inputs['w_care_g']:.1f} ％"),
    ]

    for who, spends in [("一時支出（夫）", inputs["h_spends"]), ("一時支出（妻）", inputs["w_spends"])]:
        for i, (use, age, amt) in enumerate(spends, start=1):
            rows.append((who, f"{i}件目 使用", "はい" if use else "いいえ"))
            rows.append((who, f"{i}件目 年齢", f"{age} 歳"))
            rows.append((who, f"{i}件目 金額（年額）", f"{amt:.1f} 万円"))

    return pd.DataFrame(rows, columns=["区分", "項目", "入力値"])


def make_chart_png(df_long: pd.DataFrame, y_col: str, title: str) -> bytes:
    set_japanese_font_for_matplotlib()
    fig = plt.figure(figsize=(10, 4.2))
    ax = fig.add_subplot(111)
    ax.plot(df_long["年目"], df_long[y_col], marker="o")
    ax.set_title(title)
    ax.set_xlabel("年目")
    ax.set_ylabel("万円")
    ax.grid(True)

    buf = BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=200)
    plt.close(fig)
    return buf.getvalue()


def build_pdf_bytes(
    df_view: pd.DataFrame,
    inputs: dict,
    df_long: pd.DataFrame,
    extra_text_blocks: Optional[List[Tuple[str, List[str]]]] = None
) -> bytes:
    try:
        pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))
        base_font = "HeiseiKakuGo-W5"
    except Exception:
        base_font = "Helvetica"

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=24, rightMargin=18, topMargin=18, bottomMargin=18
    )
    styles = getSampleStyleSheet()
    styleN = styles["Normal"]
    styleN.fontName = base_font
    styleN.fontSize = 9
    styleN.leading = 12

    elems = []
    elems.append(Paragraph(f"<b>{APP_TITLE}</b>", styleN))
    elems.append(Spacer(1, 8))

    elems.append(Paragraph("<b>入力値一覧</b>", styleN))
    elems.append(Spacer(1, 6))

    in_df = build_inputs_table(inputs)
    in_data = [list(in_df.columns)]
    for _, r in in_df.iterrows():
        in_data.append([str(r["区分"]), str(r["項目"]), str(r["入力値"])])

    in_tbl = Table(in_data, repeatRows=1)
    ts = TableStyle()
    ts.add("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e88e5"))
    ts.add("TEXTCOLOR", (0, 0), (-1, 0), colors.white)
    ts.add("FONTNAME", (0, 0), (-1, -1), base_font)
    ts.add("FONTSIZE", (0, 0), (-1, -1), 8)
    ts.add("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d0d0d0"))
    ts.add("VALIGN", (0, 0), (-1, -1), "MIDDLE")
    ts.add("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fbff")])
    ts.add("ALIGN", (0, 0), (-1, -1), "LEFT")
    in_tbl.setStyle(ts)
    elems.append(in_tbl)

    elems.append(PageBreak())

    elems.append(Paragraph("<b>計算結果（ライフプラン表）</b>", styleN))
    elems.append(Spacer(1, 6))

    all_cols = list(df_view.columns)
    first_col = all_cols[0]
    year_cols = all_cols[1:]

    cols_per_page = 20
    chunks = [year_cols[i:i+cols_per_page] for i in range(0, len(year_cols), cols_per_page)]

    def row_bg(label: str):
        if label.startswith("収入合計"):
            return colors.HexColor("#00b0f0"), colors.white
        if label.startswith("支出合計"):
            return colors.HexColor("#ff0000"), colors.white
        if label.startswith("貯蓄残高"):
            return colors.HexColor("#92d050"), colors.black
        if label.startswith("単身期開始"):
            return colors.HexColor("#fff4c2"), colors.black
        return None, None

    def is_blank(v):
        if v is None:
            return True
        try:
            if isinstance(v, float) and pd.isna(v):
                return True
        except Exception:
            pass
        sv = str(v).strip()
        return (sv == "" or sv.lower() == "nan")

    for ci, ch in enumerate(chunks):
        page_cols = [first_col] + ch
        sub = df_view[page_cols].copy()

        data = [page_cols]
        for _, r in sub.iterrows():
            row = []
            label = str(r[first_col])
            for j, c in enumerate(page_cols):
                v = r[c]
                if j == 0:
                    row.append("" if v is None else str(v))
                else:
                    if is_blank(v):
                        row.append("")
                    else:
                        try:
                            if label in ["夫年齢", "妻年齢"]:
                                row.append(str(int(float(v))))
                            else:
                                if label.startswith("単身期開始"):
                                    row.append(str(v))
                                else:
                                    row.append(f"{float(v):.1f}")
                        except Exception:
                            row.append(str(v))
            data.append(row)

        usable_w = doc.width
        first_w = 165
        n_year = len(page_cols) - 1
        rest_w = max(usable_w - first_w, 10)
        each_w = rest_w / max(n_year, 1)
        col_widths = [first_w] + [each_w] * n_year

        tbl = Table(data, repeatRows=1, colWidths=col_widths)
        ts2 = TableStyle()
        ts2.add("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6"))
        ts2.add("FONTNAME", (0, 0), (-1, -1), base_font)
        ts2.add("FONTSIZE", (0, 0), (-1, -1), 8)
        ts2.add("ALIGN", (1, 0), (-1, -1), "CENTER")
        ts2.add("ALIGN", (0, 0), (0, -1), "LEFT")
        ts2.add("VALIGN", (0, 0), (-1, -1), "MIDDLE")
        ts2.add("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d0d0d0"))
        ts2.add("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fcfcfc")])
        ts2.add("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#fafafa"))

        for i in range(1, len(data)):
            label = data[i][0]
            bg, fg = row_bg(label)
            if bg is not None:
                ts2.add("BACKGROUND", (0, i), (-1, i), bg)
                ts2.add("TEXTCOLOR", (0, i), (-1, i), fg)

        tbl.setStyle(ts2)
        elems.append(tbl)

        if ci < len(chunks) - 1:
            elems.append(PageBreak())

    elems.append(PageBreak())
    elems.append(Paragraph("<b>グラフ</b>", styleN))
    elems.append(Spacer(1, 8))

    png1 = make_chart_png(df_long, "年間現金収支(万円)", "年間現金収支（万円）")
    png2 = make_chart_png(df_long, "貯蓄残高(万円)", "貯蓄残高（万円）")

    img1 = RLImage(BytesIO(png1), width=720, height=300)
    img2 = RLImage(BytesIO(png2), width=720, height=300)

    elems.append(img1)
    elems.append(Spacer(1, 10))
    elems.append(img2)

    if extra_text_blocks:
        elems.append(PageBreak())
        elems.append(Paragraph("<b>アドバイス</b>", styleN))
        elems.append(Spacer(1, 8))
        for title, lines in extra_text_blocks:
            elems.append(Paragraph(f"<b>{html.escape(title)}</b>", styleN))
            elems.append(Spacer(1, 4))
            for ln in lines:
                elems.append(Paragraph(html.escape(str(ln)), styleN))
            elems.append(Spacer(1, 10))

    doc.build(elems)
    return buf.getvalue()


def _get_row_vals(df_table: pd.DataFrame, label: str):
    if df_table is None or label not in df_table.index:
        return None
    vals = []
    for v in df_table.loc[label].tolist():
        try:
            vals.append(float(v) if v != "" else 0.0)
        except:
            vals.append(0.0)
    return vals


def make_money_advice_soft(df_long: pd.DataFrame, df_table: pd.DataFrame) -> List[str]:
    if df_long is None or len(df_long) == 0:
        return ["まだ計算結果がありません。入力後に「計算」を押してください。"]

    cash = df_long["年間現金収支(万円)"].astype(float).reset_index(drop=True)
    bal  = df_long["貯蓄残高(万円)"].astype(float).reset_index(drop=True)
    years = df_long["年目"].astype(int).reset_index(drop=True)

    min_bal  = float(bal.min())
    last_bal = float(bal.iloc[-1])

    deficit_mask = cash < 0
    deficit_years = years[deficit_mask].tolist()
    deficit_count = int(deficit_mask.sum())

    max_streak = 0
    best_end_idx = None
    cur = 0
    for i, is_def in enumerate(deficit_mask.tolist()):
        if is_def:
            cur += 1
            if cur > max_streak:
                max_streak = cur
                best_end_idx = i
        else:
            cur = 0

    total_deficit = float((-cash[deficit_mask]).sum()) if deficit_count > 0 else 0.0

    worst_block_deficit = 0.0
    worst_block_min_bal = None
    worst_block_years = None
    if max_streak and best_end_idx is not None:
        start = best_end_idx - max_streak + 1
        end = best_end_idx
        block_cash = cash.iloc[start:end+1]
        worst_block_deficit = float((-block_cash[block_cash < 0]).sum())
        worst_block_min_bal = float(bal.iloc[start:end+1].min())
        worst_block_years = (int(years.iloc[start]), int(years.iloc[end]))

    care_h = _get_row_vals(df_table, "介護費 夫")
    care_w = _get_row_vals(df_table, "介護費 妻")
    spend_h = _get_row_vals(df_table, "一時支出 夫")
    spend_w = _get_row_vals(df_table, "一時支出 妻")

    item_rows = [_get_row_vals(df_table, nm) for nm in ITEMS]
    living_total = None
    if all(r is not None for r in item_rows):
        living_total = [sum(r[i] for r in item_rows) for i in range(len(item_rows[0]))]

    advice = []

    if min_bal < 0:
        neg_idx = [i for i, v in enumerate(bal.tolist()) if v < 0]
        first_neg = neg_idx[0] if neg_idx else None
        last_neg = neg_idx[-1] if neg_idx else None

        if first_neg is not None:
            first_year = int(years.iloc[first_neg])
            last_year = int(years.iloc[last_neg])

            stays_negative = all(v < 0 for v in bal.iloc[first_neg:].tolist())

            if stays_negative:
                advice.append(f"🔴 {first_year}年目から貯蓄残高がマイナスに入り、その状態が最後まで続きます（資金ショート想定）。早めの手当てが必要です。")
            else:
                advice.append(f"🔴 {first_year}年目に貯蓄残高がマイナスに入ります（いったん{last_year}年目までマイナスが出ます）。早めに対策を考えると安心です。")
    else:
        if deficit_count == 0:
            advice.append("🟢 全体としてとても安定しています（残高も収支も大きな不安が出にくい形です）。")
        else:
            advice.append("🟠 年間収支が赤字になる年はありますが、残高がマイナスにはなっていません。落ち着いて確認していきましょう。")

    if min_bal >= 0:
        advice.append("🌱 シミュレーション期間を通して、貯蓄残高はマイナスになっていません（資金ショートしにくい想定です）。")

    if deficit_count == 0:
        advice.append("😊 年間の現金収支は全期間でプラスです。大きな支出イベントの年だけ、念のため見ておくと十分です。")
    else:
        advice.append(
            f"📉 年間の現金収支が赤字になる年が {deficit_count} 年あります（連続最大 {max_streak} 年）。"
            f"赤字合計は {total_deficit:,.1f} 万円ほどです。"
        )

    advice.append(f"🏁 最終年の貯蓄残高（目安）：{last_bal:,.1f} 万円")
    advice.append("💡 ヒント：①一時支出は“時期調整”だけでも効きます ②生活費は“固定費”から ③介護費は少し多め想定で安心です")
    return advice


def make_inheritance_advice_soft(inputs: dict, df_long: pd.DataFrame) -> List[str]:
    if inputs is None or df_long is None or len(df_long) == 0:
        return ["相続アドバイスは、計算後に表示されます。"]

    h_now, h_die = int(inputs["h_now"]), int(inputs["h_die"])
    w_now, w_die = int(inputs["w_now"]), int(inputs["w_die"])

    h_year = (h_die - h_now + 1) if h_die >= h_now else None
    w_year = (w_die - w_now + 1) if w_die >= w_now else None

    def bal_at(year_after: int):
        if year_after is None:
            return None
        if year_after < 1 or year_after > int(df_long["年目"].max()):
            return None
        return float(df_long.loc[df_long["年目"] == year_after, "貯蓄残高(万円)"].iloc[0])

    h_bal = bal_at(h_year)
    w_bal = bal_at(w_year)

    advice = []
    advice.append("🕊️ 相続については、まず『いつ頃』『どれくらい残る見込みか』をざっくり掴むだけでも大きな前進です。")

    if h_year is not None:
        hb = (h_bal if h_bal is not None else 0.0)
        advice.append(f"・夫が {h_die}歳（{h_year}年目）時点の貯蓄残高目安：{hb:,.1f} 万円")
    if w_year is not None:
        wb = (w_bal if w_bal is not None else 0.0)
        advice.append(f"・妻が {w_die}歳（{w_year}年目）時点の貯蓄残高目安：{wb:,.1f} 万円")

    last_bal = float(df_long["貯蓄残高(万円)"].iloc[-1])
    if last_bal >= 3600.0:
        advice.append("💰 最終的な貯蓄残高が3,600万円を超えそうです。ほかの資産（不動産・保険・有価証券等）を踏まえると、相続税が課税される可能性があります。『概算だけ』でも専門家に確認しておくと安心です。")

    advice.append("🌿 次の3点を、できる範囲で整えておくと安心です：")
    advice.append("　① 遺言（特に不動産がある場合は有効）")
    advice.append("　② もしもの時の連絡先・口座・保険・不動産情報の一覧（家族が困りにくくなります）")
    advice.append("　③ 生前贈与や名義の整理は『急がず、税や手間を見ながら』でOKです")
    advice.append("📌 相続税が気になる規模になりそうなら、専門家に『概算だけ』相談しておくと、安心材料が増えます。")
    return advice


def make_chatgpt_link(question_text: str) -> str:
    return "https://chat.openai.com/"


# =========================
# 入力フォーム
# =========================
with st.form("lifeplan_form", clear_on_submit=False):

    st.markdown('<div class="section-title">■ 年齢・貯蓄</div>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 1.4])
    with c1:
        h_now = NI_INT("夫の現在年齢", "h_now", 0, 120, DEFAULT["h_now"], 1)
    with c2:
        h_die = NI_INT("夫の死亡年齢", "h_die", 0, 120, DEFAULT["h_die"], 1)
    with c3:
        w_now = NI_INT("妻の現在年齢", "w_now", 0, 120, DEFAULT["w_now"], 1)
    with c4:
        w_die = NI_INT("妻の死亡年齢", "w_die", 0, 120, DEFAULT["w_die"], 1)
    with c5:
        start_savings = NI_FLOAT("夫婦合計の現在貯蓄額（万円）", "start_savings", 0.0, 999999.0, DEFAULT["start_savings"], 0.1)

    st.divider()

    st.markdown('<div class="section-title">■ 収入（手取り年収：年額・万円）</div>', unsafe_allow_html=True)
    L, R = st.columns(2)

    with L:
        st.markdown("**夫**")
        a = st.columns([1.2, 1.0, 1.2, 1.2, 1.0])
        with a[0]:
            h_inc_now = NI_FLOAT("現在年収(万円)", "h_inc_now", 0.0, 20000.0, DEFAULT["h_inc_now"], 0.1)
        with a[1]:
            h_g1 = NI_FLOAT("上昇率(％)", "h_g1", -100.0, 100.0, DEFAULT["h_g1"], 0.1)
        with a[2]:
            h_ch_age = NI_INT("変更(何歳から)", "h_ch_age", 0, 120, DEFAULT["h_ch_age"], 1)
        with a[3]:
            h_inc_after = NI_FLOAT("変更後年収(万円)", "h_inc_after", 0.0, 20000.0, DEFAULT["h_inc_after"], 0.1)
        with a[4]:
            h_g2 = NI_FLOAT("上昇率(％)", "h_g2", -100.0, 100.0, DEFAULT["h_g2"], 0.1)
        st.caption("※年金、給料、パート代、利息、配当金など（株式や不動産等の含み益は入れないでください）")

        h_lumps = build_lumps(
            "h_lump",
            "夫の一時収入（年額・万円）",
            DEFAULT["h_lump"],
            note_text="※退職金、親からの相続、不動産売却など　※数値入力後、計算に反映させるため必ず右の使用ボタン欄を☑にしてください"
        )

    with R:
        st.markdown("**妻**")
        b = st.columns([1.2, 1.0, 1.2, 1.2, 1.0])
        with b[0]:
            w_inc_now = NI_FLOAT("現在年収(万円)", "w_inc_now", 0.0, 20000.0, DEFAULT["w_inc_now"], 0.1)
        with b[1]:
            w_g1 = NI_FLOAT("上昇率(％)", "w_g1", -100.0, 100.0, DEFAULT["w_g1"], 0.1)
        with b[2]:
            w_ch_age = NI_INT("変更(何歳から)", "w_ch_age", 0, 120, DEFAULT["w_ch_age"], 1)
        with b[3]:
            w_inc_after = NI_FLOAT("変更後年収(万円)", "w_inc_after", 0.0, 20000.0, DEFAULT["w_inc_after"], 0.1)
        with b[4]:
            w_g2 = NI_FLOAT("上昇率(％)", "w_g2", -100.0, 100.0, DEFAULT["w_g2"], 0.1)

        w_lumps = build_lumps(
            "w_lump",
            "妻の一時収入（年額・万円）",
            DEFAULT["w_lump"],
            note_text=None
        )

    st.divider()

    st.markdown('<div class="section-title">■ 生活費（8項目：月額・万円/月）</div>', unsafe_allow_html=True)
    st.markdown('<div class="subnote">変更条件は「何年後から」。</div>', unsafe_allow_html=True)

    living_params = {}
    living_sum_now_m = 0.0
    living_sum_after_m = 0.0

    for name in ITEMS:
        d = DEFAULT["living"][name]
        st.markdown(f"**{name}**")
        cols = st.columns([1.1, 0.9, 1.0, 1.1, 0.9])
        with cols[0]:
            m = NI_FLOAT("月額(万円/月)", f"lv_{name}_m", 0.0, 99999.0, d["m"], 0.1)
        with cols[1]:
            g = NI_FLOAT("上昇率(％)", f"lv_{name}_g", -100.0, 100.0, d["g"], 0.1)
        with cols[2]:
            after_years = NI_INT("変更(何年後から)", f"lv_{name}_after", 0, 60, d["after_years"], 1)
        with cols[3]:
            m2 = NI_FLOAT("変更後月額(万円/月)", f"lv_{name}_m2", 0.0, 99999.0, d["m2"], 0.1)
        with cols[4]:
            g2 = NI_FLOAT("上昇率(％)", f"lv_{name}_g2", -100.0, 100.0, d["g2"], 0.1)

        living_params[name] = dict(m=float(m), g=float(g), after_years=int(after_years), m2=float(m2), g2=float(g2))

        living_sum_now_m += float(m)
        living_sum_after_m += float(m2)

        if name == "その他":
            st.markdown(
                '<div style="font-size:0.80rem;color:#666;margin-top:-0.35rem;">'
                '※例えば、あと10年間住宅ローンが残っているような場合には月額欄にその金額を、変更欄に10を、変更後月額欄に0を入力することで対応できます'
                '</div>',
                unsafe_allow_html=True
            )
        st.markdown("---")

    st.markdown("### 生活費 合計（月額）")
    left, right = st.columns([1.25, 1.75])

    with left:
        s1, s2 = st.columns(2)
        with s1:
            st.metric("現在 合計（万円/月）", f"{living_sum_now_m:,.1f}")
        with s2:
            st.metric("変更後 合計（万円/月）", f"{living_sum_after_m:,.1f}")

    with right:
        st.markdown("#### 単身世帯になったときの生活費の割合(％)")
        single_ratio_pct = NI_INT("", "single_ratio_pct", 0, 200, DEFAULT["single_ratio_pct"], 1, label_visibility="collapsed")
        st.markdown(
            '<div style="font-size:0.85rem;color:#666;margin-top:-0.25rem;">'
            '※夫婦世帯最終年の生活費に対する割合を入力してください'
            '</div>',
            unsafe_allow_html=True
        )

    st.divider()

    st.markdown('<div class="section-title">■ 介護費用（月額・万円/月）</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**夫**")
        h_care_start = NI_INT("何歳から", "h_care_start", 0, 120, DEFAULT["h_care_start"], 1)
        h_care_m = NI_FLOAT("月額(万円/月)", "h_care_m", 0.0, 99999.0, DEFAULT["h_care_m"], 0.1)
        h_care_g = NI_FLOAT("上昇率(％)", "h_care_g", -100.0, 100.0, DEFAULT["h_care_g"], 0.1)
        st.markdown(
            '<div style="font-size:0.85rem;color:#666;margin-top:-0.20rem;">'
            '※介護施設への入居一時金が必要な場合には、下の一時支出欄で入力してください'
            '</div>',
            unsafe_allow_html=True
        )
    with c2:
        st.markdown("**妻**")
        w_care_start = NI_INT("何歳から", "w_care_start", 0, 120, DEFAULT["w_care_start"], 1)
        w_care_m = NI_FLOAT("月額(万円/月)", "w_care_m", 0.0, 99999.0, DEFAULT["w_care_m"], 0.1)
        w_care_g = NI_FLOAT("上昇率(％)", "w_care_g", -100.0, 100.0, DEFAULT["w_care_g"], 0.1)

    st.divider()

    L2, R2 = st.columns(2)
    with L2:
        h_spends = build_lumps(
            "h_spend",
            "夫の一時支出（年額・万円）",
            DEFAULT["h_spend"],
            note_text="※車買換え、海外旅行、子の結婚費用、配偶者の葬式代など　※数値入力後、計算に反映させるため必ず右の使用ボタン欄を☑にしてください"
        )
    with R2:
        w_spends = build_lumps(
            "w_spend",
            "妻の一時支出（年額・万円）",
            DEFAULT["w_spend"],
            note_text=None
        )

    st.markdown('<div class="section-title">■ 実行</div>', unsafe_allow_html=True)
    bL, bC, bR = st.columns([1, 2, 1])
    with bC:
        submitted = st.form_submit_button("計算", type="primary", use_container_width=True)


# =========================
# 計算・表示
# =========================
if "result_long" not in st.session_state: st.session_state["result_long"] = None
if "result_table" not in st.session_state: st.session_state["result_table"] = None
if "pdf_bytes" not in st.session_state: st.session_state["pdf_bytes"] = None
if "inputs" not in st.session_state: st.session_state["inputs"] = None

if submitted:
    if int(h_die) < int(h_now):
        st.error("夫：死亡年齢は現在年齢以上にしてください。"); st.stop()
    if int(w_die) < int(w_now):
        st.error("妻：死亡年齢は現在年齢以上にしてください。"); st.stop()

    inputs = {
        "h_now": int(h_now), "h_die": int(h_die),
        "w_now": int(w_now), "w_die": int(w_die),
        "start_savings": float(start_savings),

        "h_inc_now": float(h_inc_now), "h_g1": float(h_g1), "h_ch_age": int(h_ch_age),
        "h_inc_after": float(h_inc_after), "h_g2": float(h_g2),

        "w_inc_now": float(w_inc_now), "w_g1": float(w_g1), "w_ch_age": int(w_ch_age),
        "w_inc_after": float(w_inc_after), "w_g2": float(w_g2),

        "living_params": living_params,
        "single_ratio_pct": int(single_ratio_pct),

        "h_care_start": int(h_care_start), "h_care_m": float(h_care_m), "h_care_g": float(h_care_g),
        "w_care_start": int(w_care_start), "w_care_m": float(w_care_m), "w_care_g": float(w_care_g),

        "h_lumps": h_lumps,
        "w_lumps": w_lumps,
        "h_spends": h_spends,
        "w_spends": w_spends,

        "h_lump_map": lumps_to_map(h_lumps),
        "w_lump_map": lumps_to_map(w_lumps),
        "h_spend_map": lumps_to_map(h_spends),
        "w_spend_map": lumps_to_map(w_spends),
    }

    df_long, df_table = calc_lifeplan(inputs)
    st.session_state["result_long"] = df_long
    st.session_state["result_table"] = df_table
    st.session_state["inputs"] = inputs

    df_view = df_view_for_display(df_table)

    money_lines = make_money_advice_soft(df_long, df_table)
    inh_lines = make_inheritance_advice_soft(inputs, df_long)

    st.session_state["pdf_bytes"] = build_pdf_bytes(
        df_view, inputs, df_long,
        extra_text_blocks=[
            ("家計へのアドバイス", money_lines),
            ("相続ワンポイントアドバイス", inh_lines),
        ]
    )

df_long = st.session_state.get("result_long", None)
df_table = st.session_state.get("result_table", None)

if df_long is not None and df_table is not None:
    st.success("計算できました。")

    tab1, tab2, tab3 = st.tabs(["表", "グラフ", "アドバイス"])

    with tab1:
        st.markdown(
            '<div style="display:flex;align-items:flex-end;gap:10px;">'
            '<div style="font-size:1.25rem;font-weight:700;">ライフプラン表（年次）</div>'
            '<div style="font-size:0.75rem;color:#666;">※各年齢における期末時点の数字を表示しています</div>'
            '</div>',
            unsafe_allow_html=True
        )
        df_view = df_view_for_display(df_table)
        st.markdown(df_to_sticky_html(df_view), unsafe_allow_html=True)

    with tab2:
        st.subheader("グラフ① 年間現金収支")
        chart_cash = (
            alt.Chart(df_long)
            .mark_line(point=True)
            .encode(
                x=alt.X("年目:Q", title="年目"),
                y=alt.Y("年間現金収支(万円):Q", title="万円"),
                tooltip=[alt.Tooltip("年目:Q", title="年目"), alt.Tooltip("年間現金収支(万円):Q", title="万円")]
            )
            .properties(height=300)
        )
        st.altair_chart(chart_cash, use_container_width=True)

        st.subheader("グラフ② 貯蓄残高")
        chart_bal = (
            alt.Chart(df_long)
            .mark_line(point=True)
            .encode(
                x=alt.X("年目:Q", title="年目"),
                y=alt.Y("貯蓄残高(万円):Q", title="万円"),
                tooltip=[alt.Tooltip("年目:Q", title="年目"), alt.Tooltip("貯蓄残高(万円):Q", title="万円")]
            )
            .properties(height=300)
        )
        st.altair_chart(chart_bal, use_container_width=True)

    with tab3:
        st.subheader("家計へのアドバイス")
        st.caption("（詳細なアドバイスは下記の質問欄からお進みください）")
        for line in make_money_advice_soft(df_long, df_table):
            st.write(line)

        st.divider()

        st.subheader("相続ワンポイントアドバイス")
        st.caption("（詳細なアドバイスは下記の質問欄からお進みください）")
        inputs = st.session_state.get("inputs", None)
        for line in make_inheritance_advice_soft(inputs, df_long):
            st.write(line)

        st.divider()

        st.subheader("相談の入口（ここから追加質問できます）")
        st.caption("下のテンプレをコピーして、このままChatGPTに貼ると、続きの相談がしやすくなります。")

        if inputs is not None:
            min_bal = float(df_long["貯蓄残高(万円)"].min())
            deficit_count = int((df_long["年間現金収支(万円)"] < 0).sum())
            template = f"""【シニア夫婦LPS：相談テンプレ】
- 夫: 現在{inputs['h_now']}歳 / 想定死亡{inputs['h_die']}歳
- 妻: 現在{inputs['w_now']}歳 / 想定死亡{inputs['w_die']}歳
- 初期貯蓄: {inputs['start_savings']:.1f}万円
- 単身生活費割合: {int(inputs.get('single_ratio_pct', 100))}%
- 収支赤字の年数: {deficit_count}年
- 最低貯蓄残高: {min_bal:.1f}万円

相談したいこと：
1)
2)
"""
        else:
            template = """【シニア夫婦LPS：相談テンプレ】
（計算後にテンプレが自動で埋まります）
相談したいこと：
1)
"""

        st.code(template, language="text")

        user_q = st.text_area(
            "ここに質問を入力（任意）",
            height=120,
            placeholder="例：赤字が続く年の対策を、生活費と介護費に分けて教えてください。"
        )

        if user_q.strip():
            st.write("✅ あなたの質問（このままChatGPTに貼れます）")
            st.code(template + "\n" + user_q.strip(), language="text")

        st.markdown("### ChatGPTを開く")
        st.link_button("ChatGPTを開く（別タブ）", make_chatgpt_link(user_q if user_q.strip() else template))

        st.caption("※アプリからChatGPTへ“自動送信”はしません（安全のため）。上の文章をコピーして貼るだけでOKです。")

    l, c, r = st.columns([1, 2, 1])
    with c:
        st.download_button(
            label="PDFで保存",
            data=st.session_state["pdf_bytes"],
            file_name="lifeplan_result.pdf",
            mime="application/pdf",
            use_container_width=True,
            type="primary"
        )
else:
    st.info("まだ計算していません。入力後、中央の「計算」ボタンを押してください。")

# ===== フッター（著作権表示）=====
st.markdown(
    "<hr><div style='text-align:center; color:#888; font-size:0.85em;'>"
    "© 作成者／無断転載・商用利用不可"
    "</div>",
    unsafe_allow_html=True
)




