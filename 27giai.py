import streamlit as st
import easyocr
import pandas as pd
import json
import numpy as np
from PIL import Image

# --- HẰNG SỐ HIỆU QUY ƯỚC ---
HIEU_CHART = {0: [0,11,22,33,44,55,66,77,88,99], 1: [9,10,21,32,43,54,65,76,87,98],
              2: [8,19,20,31,42,53,64,75,86,97], 3: [7,18,29,30,41,52,63,74,85,96],
              4: [6,17,28,39,40,51,62,73,84,95], 5: [5,16,27,38,49,50,61,72,83,94],
              6: [4,15,26,37,48,59,60,71,82,93], 7: [3,14,25,36,47,58,69,70,81,92],
              8: [2,13,24,35,46,57,68,79,80,91], 9: [1,12,23,34,45,56,67,78,89,90]}

st.set_page_config(page_title="App 27 Giải Pro - Tuấn Phong", layout="wide")

if 'db' not in st.session_state:
    st.session_state.db = {"bang_b_points": [], "current_raw": [], "history": []}

if st.sidebar.button("❌ RESET ALL", use_container_width=True):
    st.session_state.db = {"bang_b_points": [], "current_raw": [], "history": []}
    st.rerun()

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['en'])

def analyze_number(num):
    s = f"{num:02d}"
    x, y = int(s[0]), int(s[1])
    h_val = next((h for h, nums in HIEU_CHART.items() if num in nums), 0)
    return {"dau": x, "duoi": y, "tong": (x + y) % 10, "hieu": h_val, "cham": [x, y]}

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Cấu hình 27 Giải")
    uploaded_file = st.file_uploader("1. Tải ảnh bảng kết quả", type=["png", "jpg", "jpeg"])
    uploaded_json = st.file_uploader("📂 Nạp dữ liệu cũ", type=["json"])
    if uploaded_json:
        st.session_state.db = json.load(uploaded_json)
    run_btn = st.button("🚀 CẬP NHẬT TỔNG LỰC", use_container_width=True)

# --- XỬ LÝ LOGIC ---
if uploaded_file and run_btn:
    reader = load_ocr()
    image = Image.open(uploaded_file)
    results = reader.readtext(np.array(image), detail=0)
    
    all_27_loto = []
    all_digits_list = []
    for text in results:
        clean_text = "".join([d for d in text if d.isdigit()])
        if len(clean_text) >= 2:
            all_27_loto.append(int(clean_text[-2:]))
            for digit in clean_text: all_digits_list.append(int(digit))
    
    all_27_loto = all_27_loto[:27] 

    if all_27_loto:
        raw = all_digits_list
        gdb_2_so = all_27_loto[0]
        rank_val, loai_val, no_30_str = "N/A", "N/A", "N/A"

        # 1. Tính toán hiệu quả dựa trên dữ liệu CŨ trước khi nạp ảnh mới
        if st.session_state.db["current_raw"] and st.session_state.db["bang_b_points"]:
            old_raw, old_pts = st.session_state.db["current_raw"], st.session_state.db["bang_b_points"]
            df_temp = pd.DataFrame([{"S": old_raw[i], **old_pts[i]} for i in range(len(old_raw))])
            
            # Tính bảng C đếm 0
            list_c_temp = []
            for i in range(10):
                m = df_temp[df_temp["S"] == i]
                list_c_temp.append({"S":i, "dau":(m["dau"]==0).sum(), "duoi":(m["duoi"]==0).sum(), "tong":(m["tong"]==0).sum(), "hieu":(m["hieu"]==0).sum(), "cham":(m["cham"]==0).sum()})
            df_c_temp = pd.DataFrame(list_c_temp)
            
            dan_scores = []
            for i in range(100):
                t = analyze_number(i)
                score = df_c_temp.iloc[t["dau"]]["dau"] + df_c_temp.iloc[t["duoi"]]["duoi"] + df_c_temp.iloc[t["tong"]]["tong"] + df_c_temp.iloc[t["hieu"]]["hieu"]
                score += (df_c_temp.iloc[t["dau"]]["cham"] * 2) if t["dau"]==t["duoi"] else (df_c_temp.iloc[t["dau"]]["cham"] + df_c_temp.iloc[t["duoi"]]["cham"])
                dan_scores.append({"SO": f"{i:02d}", "DIEM": score})
            
            df_rank = pd.DataFrame(dan_scores).sort_values("DIEM", ascending=True).reset_index(drop=True)
            
            # Tính Rank GĐB
            rank_found = df_rank[df_rank["SO"] == f"{gdb_2_so:02d}"].index
            if len(rank_found) > 0:
                rank_val = int(rank_found[0]) + 1
                loai_val = "A" if rank_val <= 70 else "T"
            
            # THỐNG KÊ NỔ 30 (Đếm xem có bao nhiêu số lô nằm trong Top 30 điểm thấp)
            top_30_list = df_rank.head(30)["SO"].tolist()
            count_hit = sum(1 for n in all_27_loto if f"{n:02d}" in top_30_list)
            no_30_str = f"{count_hit}/30"

        # 2. CẬP NHẬT ĐIỂM BẢNG B
        targets = [analyze_number(n) for n in all_27_loto]
        s_dau, s_duoi, s_tong, s_hieu = {t["dau"] for t in targets}, {t["duoi"] for t in targets}, {t["tong"] for t in targets}, {t["hieu"] for t in targets}
        s_cham = set(); [s_cham.update(t["cham"]) for t in targets]

        if not st.session_state.db["current_raw"]:
            st.session_state.db["bang_b_points"] = [{"dau":1,"duoi":1,"tong":1,"hieu":1,"cham":1} for _ in range(len(raw))]
        else:
            pts_db, old_raw_db = st.session_state.db["bang_b_points"], st.session_state.db["current_raw"]
            for i in range(min(len(old_raw_db), len(pts_db))):
                val, p = old_raw_db[i], pts_db[i]
                p["dau"] = 0 if val in s_dau else p["dau"] + 1
                p["duoi"] = 0 if val in s_duoi else p["duoi"] + 1
                p["tong"] = 0 if val in s_tong else p["tong"] + 1
                p["hieu"] = 0 if val in s_hieu else p["hieu"] + 1
                p["cham"] = 0 if val in s_cham else p["cham"] + 1

        # 3. Lưu Lịch sử
        st.session_state.db["history"].insert(0, {
            "Kỳ": len(st.session_state.db["history"]) + 1,
            "GĐB": f"{gdb_2_so:02d}",
            "Vị trí": rank_val,
            "Loại": loai_val,
            "Nổ 30": no_30_str
        })
        st.session_state.db["current_raw"] = raw
        st.success(f"Đã cập nhật 27 giải. GĐB: {gdb_2_so:02d}")
    else:
        st.error("Không đọc được ảnh!")

# --- HIỂN THỊ ---
if st.session_state.db["current_raw"] and st.session_state.db["bang_b_points"]:
    raw, pts = st.session_state.db["current_raw"], st.session_state.db["bang_b_points"]
    df_b = pd.DataFrame([{"SO VE": raw[i], **pts[i]} for i in range(len(raw))])
    
    # Bảng C đếm 0
    list_c = []
    for i in range(10):
        m = df_b[df_b["SO VE"] == i]
        list_c.append({"SO":i, "C DAU":(m["dau"]==0).sum(), "C DUOI":(m["duoi"]==0).sum(), "C TONG":(m["tong"]==0).sum(), "C HIEU":(m["hieu"]==0).sum(), "C CHAM":(m["cham"]==0).sum()})
    df_c = pd.DataFrame(list_c)

    dan_all = []
    for i in range(100):
        t = analyze_number(i)
        score = df_c.iloc[t["dau"]]["C DAU"] + df_c.iloc[t["duoi"]]["C DUOI"] + df_c.iloc[t["tong"]]["C TONG"] + df_c.iloc[t["hieu"]]["C HIEU"]
        score += (df_c.iloc[t["dau"]]["C CHAM"] * 2) if t["dau"]==t["duoi"] else (df_c.iloc[t["dau"]]["C CHAM"] + df_c.iloc[t["duoi"]]["C CHAM"])
        dan_all.append({"SO": f"{i:02d}", "DIEM": int(score)})
    
    df_dan = pd.DataFrame(dan_all).sort_values("DIEM", ascending=True)

    # UI DÀN SỐ
    st.write("### 🎯 DÀN SỐ (ƯU TIÊN ĐIỂM THẤP)")
    c1, c2 = st.columns(2)
    with c1:
        n1 = st.number_input("Dàn 1:", 1, 100, 49)
        st.text_area("Dàn 1 (Thấp -> Cao):", value=" ".join(df_dan.head(n1)["SO"].tolist()), height=120)
    with c2:
        n2 = st.number_input("Dàn 2:", 1, 100, 30)
        st.text_area("Dàn 30 (Siêu phẩm):", value=" ".join(df_dan.head(n2)["SO"].tolist()), height=120)

    # TABS
    t_hist, t_c, t_b, t_a = st.tabs(["🕒 Lịch sử", "🗂️ Bảng C & D", "🎲 Bảng B", "📊 Bảng A"])
    
    with t_hist:
        st.subheader("Bảng Lịch sử & Thống kê Nổ 30")
        st.table(pd.DataFrame(st.session_state.db["history"]))
    
    with t_c:
        st.subheader("Bảng C (Tần suất vừa nổ)")
        st.table(df_c)
        st.subheader("Bảng D (Ma trận 100 số - Thấp lên Cao)")
        st.dataframe(df_dan.set_index("SO").T, use_container_width=True)
    
    with t_b: st.dataframe(df_b, use_container_width=True)
    with t_a: 
        with st.expander("Xem 107 vị trí"): st.dataframe(pd.DataFrame([{"VT": i+1, "Số": raw[i]} for i in range(len(raw))]).T)

    st.sidebar.download_button("💾 SAO LƯU", json.dumps(st.session_state.db), "data_27_giai.json")