import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Nhập các hàm xử lý từ file utils.py vừa tạo ở trên
from utils import parse_txt_to_df, parse_dxf_to_df, detect_crs, compute_convex_hull

# Cấu hình Web App hiển thị rộng toàn màn hình
st.set_page_config(page_title="Trắc Địa WebApp", page_icon="📐", layout="wide")

st.title("📐 Web App Xử lý Số liệu Trắc địa (Phương án 1)")
st.caption("Nền tảng: Python + Streamlit | Render đồ thị: Plotly 3D trên Trình duyệt")

# Khởi tạo bộ nhớ tạm (Session State) để giữ lại dữ liệu khi người dùng chuyển bước
if 'bm1_df' not in st.session_state: st.session_state.bm1_df = None
if 'bm2_df' not in st.session_state: st.session_state.bm2_df = None

# Thanh menu bên trái (Sidebar)
st.sidebar.header("📌 QUY TRÌNH THỰC HIỆN")
step = st.sidebar.radio("Chọn bước:", [
    "🔥 [BƯỚC 1] Xác lập bề mặt tính toán",
    "🗺️ [BƯỚC 2] Xây dựng Boundary tổng quát",
    "⚙️ [BƯỚC 3-5] Các bước tiếp theo"
])

# -------------------- XỬ LÝ [BƯỚC 1] --------------------
if "BƯỚC 1" in step:
    st.header("⚙️ [BƯỚC 1] Xác lập Bề mặt tính toán (Bề mặt 1)")
    
    file_b1 = st.file_uploader("Tải file Mặt bằng hiện hữu (Định dạng: .txt, .csv, .dxf):", type=["txt", "csv", "dxf"])
    
    if file_b1 is not None:
        ext = file_b1.name.split('.')[-1].lower()
        df_raw = parse_txt_to_df(file_b1) if ext in ['txt', 'csv'] else parse_dxf_to_df(file_b1)
        
        if df_raw is not None:
            st.success(f"Đã tải thành công file! Tìm thấy {len(df_raw)} điểm dữ liệu.")
            
            # Giao diện chọn gán cột tọa độ
            cols = list(df_raw.columns)
            c1, c2, c3, c4 = st.columns(4)
            with c1: x_col = st.selectbox("Cột tọa độ X:", cols, index=1 if len(cols)>1 else 0)
            with c2: y_col = st.selectbox("Cột tọa độ Y:", cols, index=0)
            with c3: z_col = st.selectbox("Cột cao độ Z:", cols, index=2 if len(cols)>2 else 0)
            with c4: id_col = st.selectbox("Cột ID (Số thứ tự):", ["-- Không có ID (Tự động thêm) --"] + cols)
            
            # Chuẩn hóa dữ liệu về định dạng chuẩn ID, X, Y, Z
            df_proc = pd.DataFrame()
            df_proc['X'] = df_raw[x_col].astype(float)
            df_proc['Y'] = df_raw[y_col].astype(float)
            df_proc['Z'] = df_raw[z_col].astype(float)
            
            if id_col == "-- Không có ID (Tự động thêm) --":
                df_proc['ID'] = range(1, len(df_proc) + 1)
            else:
                df_proc['ID'] = df_raw[id_col]
            
            df_proc = df_proc[['ID', 'X', 'Y', 'Z']]
            
            # Hiển thị kết quả nhận diện CRS
            st.info(f"🤖 **Hệ tọa độ tự động nhận dạng:** {detect_crs(df_proc, 'X', 'Y')}")
            st.write("📊 **Xem trước dữ liệu tập điểm đã chuẩn hóa:**")
            st.dataframe(df_proc.head(15), use_container_width=True)
            
            if st.button("💾 Xác nhận & Lưu dữ liệu Bề mặt 1"):
                st.session_state.bm1_df = df_proc
                st.success("Đã khóa số liệu Bề mặt 1. Hãy chuyển sang Bước 2 ở menu bên trái!")
        else:
            st.error("Lỗi: Không đọc được dữ liệu. Kiểm tra lại định dạng file.")

# -------------------- XỬ LÝ [BƯỚC 2] --------------------
elif "BƯỚC 2" in step:
    st.header("🗺️ [BƯỚC 2] Xây dựng Boundary tổng quát")
    
    if st.session_state.bm1_df is None:
        st.warning("⚠️ Cảnh báo: Vui lòng quay lại [BƯỚC 1] để tải và cấu hình dữ liệu Bề mặt 1 trước.")
    else:
        pa_tinh = st.radio("Chọn Phương án tính toán:", ["1. Tính theo Cao độ thiết kế", "2. Tính so với Mặt bằng cơ sở (Bề mặt 2)"])
        
        boundary_mode = ""
        z_design = 0.0
        
        if "1." in pa_tinh:
            z_design = st.number_input("Nhập giá trị cao độ thiết kế (m):", value=0.0)
            boundary_mode = st.selectbox("Hình thức xác định ranh giới (Boundary):", ["Mặt bằng hiện hữu (Lấy theo Convex Hull Bề mặt 1)", "Ranh giới ấn định (Tải file ranh ngoài)"])
        else:
            st.subheader("📍 Xác lập Bề mặt cơ sở (Bề mặt 2)")
            file_b2 = st.file_uploader("Tải file Mặt bằng cơ sở (Bề mặt 2):", type=["txt", "csv", "dxf"])
            if file_b2 is not None:
                ext2 = file_b2.name.split('.')[-1].lower()
                df_raw_2 = parse_txt_to_df(file_b2) if ext2 in ['txt', 'csv'] else parse_dxf_to_df(file_b2)
                if df_raw_2 is not None:
                    df_proc_2 = pd.DataFrame()
                    df_proc_2['X'] = df_raw_2.iloc[:, 0 if len(df_raw_2.columns)==3 else 1].astype(float)
                    df_proc_2['Y'] = df_raw_2.iloc[:, 1 if len(df_raw_2.columns)==3 else 0].astype(float)
                    df_proc_2['Z'] = df_raw_2.iloc[:, 2].astype(float)
                    st.session_state.bm2_df = df_proc_2
                    st.success("Đã nạp xong số liệu Bề mặt 2.")
            
            boundary_mode = st.selectbox("Hình thức xác định ranh giới (Boundary):", [
                "Mặt bằng hiện hữu (Từ Bề mặt 1)", 
                "Tổng hợp Bề mặt 1 & 2 (Hợp nhất ranh giới)",
                "Xác định riêng biệt ranh giới Bề mặt 1 & 2"
            ])

        # ---- DỰNG ĐỒ THỊ 3D MÔ HÌNH VÀ RANH GIỚI ----
        st.subheader("📊 Mô hình trực quan 3D không gian")
        
        bm1_pts = st.session_state.bm1_df[['X', 'Y']].values
        hull_b1 = compute_convex_hull(bm1_pts)
        
        fig = go.Figure()
        
        # Vẽ các điểm Mass Points của bề mặt hiện hữu
        fig.add_trace(go.Scatter3d(
            x=st.session_state.bm1_df['X'], y=st.session_state.bm1_df['Y'], z=st.session_state.bm1_df['Z'],
            mode='markers', marker=dict(size=3, color='blue'), name='Điểm Mặt bằng 1'
        ))
        
        # Vẽ đường ranh Boundary dựa theo thuật toán đã chọn
        if "Mặt bằng hiện hữu" in boundary_mode:
            z_flat = np.full(len(hull_b1), st.session_state.bm1_df['Z'].min())
            fig.add_trace(go.Scatter3d(
                x=hull_b1[:, 0], y=hull_b1[:, 1], z=z_flat,
                mode='lines', line=dict(color='red', width=4), name='Boundary Convex Hull'
            ))
        elif "Tổng hợp Bề mặt 1 & 2" in boundary_mode and st.session_state.bm2_df is not None:
            bm2_pts = st.session_state.bm2_df[['X', 'Y']].values
            all_pts = np.vstack([bm1_pts, bm2_pts])
            hull_comb = compute_convex_hull(all_pts)
            z_flat = np.full(len(hull_comb), min(st.session_state.bm1_df['Z'].min(), st.session_state.bm2_df['Z'].min()))
            fig.add_trace(go.Scatter3d(
                x=hull_comb[:, 0], y=hull_comb[:, 1], z=z_flat,
                mode='lines', line=dict(color='purple', width=4), name='Boundary Hợp Nhất'
            ))

        # Nếu có bề mặt 2, thêm các điểm bề mặt 2 vào không gian đồ thị
        if "2." in pa_tinh and st.session_state.bm2_df is not None:
            fig.add_trace(go.Scatter3d(
                x=st.session_state.bm2_df['X'], y=st.session_state.bm2_df['Y'], z=st.session_state.bm2_df['Z'],
                mode='markers', marker=dict(size=3, color='green'), name='Điểm Mặt bằng 2'
            ))
        elif "1." in pa_tinh:
            # Mô phỏng mặt phẳng cao độ thiết kế phẳng sinh động
            x_m = np.linspace(st.session_state.bm1_df['X'].min(), st.session_state.bm1_df['X'].max(), 2)
            y_m = np.linspace(st.session_state.bm1_df['Y'].min(), st.session_state.bm1_df['Y'].max(), 2)
            X_grid, Y_grid = np.meshgrid(x_m, y_m)
            Z_grid = np.full(X_grid.shape, z_design)
            fig.add_trace(go.Surface(x=X_grid, y=Y_grid, z=Z_grid, opacity=0.4, showscale=False, name='Mặt phẳng thiết kế'))

        fig.update_layout(
            scene=dict(xaxis_title='X (m)', yaxis_title='Y (m)', zaxis_title='Z (m)', aspectmode='data'),
            margin=dict(l=0, r=0, b=0, t=30), height=600
        )
        st.plotly_chart(fig, use_container_width=True)

# -------------------- CÁC BƯỚC TIẾP THEO --------------------
else:
    st.header("🧱 Trình tự tiếp tục lập trình hệ thống")
    st.info("Khu vực này sẽ là nơi viết tiếp mã nguồn cho các thuật toán nội suy của Bước 3, 4 và 5.")
