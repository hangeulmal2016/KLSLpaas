import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from utils import parse_txt_to_df, parse_dxf_to_df, detect_crs_and_headings, compute_convex_hull

st.set_page_config(page_title="Web App Trắc Địa Mobile", page_icon="📐", layout="wide")
st.title("📐 Web App Xử lý Số liệu Trắc địa")
st.caption("Phương án 1 | Tối ưu hóa giao diện co giãn hiển thị mượt mà trên Smartphone")

if 'bm1_df' not in st.session_state: st.session_state.bm1_df = None
if 'bm2_df' not in st.session_state: st.session_state.bm2_df = None
if 'ranh_an_dinh_df' not in st.session_state: st.session_state.ranh_an_dinh_df = None

st.sidebar.header("📌 QUY TRÌNH THỰC HIỆN")
step = st.sidebar.radio("Chọn bước ứng dụng:", [
    "🔥 [BƯỚC 1] Xác lập bề mặt tính toán 1",
    "🗺️ [BƯỚC 2] Xây dựng Boundary tổng quát",
    "🧱 [BƯỚC 3-5] Các bước xử lý tiếp theo"
])

def process_surface_upload(uploaded_file, key_prefix):
    ext = uploaded_file.name.split('.')[-1].lower()
    df_raw = parse_txt_to_df(uploaded_file) if ext in ['txt', 'csv'] else parse_dxf_to_df(uploaded_file)
    if df_raw is not None:
        crs_name, headings = detect_crs_and_headings(df_raw)
        st.info(f"🤖 Hệ tọa độ nhận dạng: {crs_name}")
        cols = list(df_raw.columns)
        c1, c2, c3, c4 = st.columns(4)
        with c1: x_col = st.selectbox("Xác nhận cột X:", cols, index=0, key=f"{key_prefix}_x")
        with c2: y_col = st.selectbox("Xác nhận cột Y:", cols, index=1 if len(cols)>1 else 0, key=f"{key_prefix}_y")
        with c3: z_col = st.selectbox("Xác nhận cột Z:", cols, index=2 if len(cols)>2 else 0, key=f"{key_prefix}_z")
        with c4: id_col = st.selectbox("Xác nhận cột ID:", ["-- Tự động thêm --"] + cols, key=f"{key_prefix}_id")
        
        df_proc = pd.DataFrame()
        df_proc['X'] = df_raw[x_col].astype(float)
        df_proc['Y'] = df_raw[y_col].astype(float)
        df_proc['Z'] = df_raw[z_col].astype(float)
        if id_col == "-- Tự động thêm --":
            df_proc['ID'] = range(1, len(df_proc) + 1)
        else:
            df_proc['ID'] = df_raw[id_col]
        return df_proc[['ID', 'X', 'Y', 'Z']]
    return None

if "BƯỚC 1" in step:
    st.header("⚙️ [BƯỚC 1] Xác lập Bề mặt 1")
    file_b1 = st.file_uploader("Tải file Mặt bằng hiện hữu (DXF/TXT/CSV):", type=["txt", "csv", "dxf"], key="upload_b1")
    if file_b1 is not None:
        df_normalized = process_surface_upload(file_b1, "b1")
        if df_normalized is not None:
            st.write("📊 Xem trước dữ liệu mẫu Bề mặt 1:")
            st.dataframe(df_normalized.head(10), use_container_width=True)
            if st.button("💾 Cập nhật tập điểm Bề mặt 1"):
                st.session_state.bm1_df = df_normalized
                st.success("Đã lưu tập điểm Bề mặt 1 thành công!")

elif "BƯỚC 2" in step:
    st.header("🗺️ [BƯỚC 2] Xây dựng Boundary tổng quát")
    if st.session_state.bm1_df is None:
        st.warning("⚠️ Vui lòng hoàn thành [BƯỚC 1] trước.")
    else:
        pa_tinh = st.radio("Chọn Phương án tính toán:", ["1. Tính theo Cao độ thiết kế", "2. Tính so với Mặt bằng cơ sở"])
        boundary_mode = "Mặt bằng hiện hữu"
        z_design = 0.0
        
        if "1." in pa_tinh:
            z_design = st.number_input("Nhập giá trị cao độ thiết kế (m):", value=0.0)
            boundary_mode = st.selectbox("Lựa chọn hình thức ranh:", ["Mặt bằng hiện hữu", "Ranh giới ấn định"], key="bm_mode_1")
            if boundary_mode == "Ranh giới ấn định":
                file_ranh = st.file_uploader("Tải file Ranh giới ấn định ngoài:", type=["txt", "csv", "dxf"], key="ranh_ad_1")
                if file_ranh is not None:
                    st.session_state.ranh_an_dinh_df = process_surface_upload(file_ranh, "rad1")
        else:
            st.subheader("📍 Xác lập Bề mặt cơ sở (Bề mặt 2)")
            file_b2 = st.file_uploader("Tải file Mặt bằng cơ sở 2:", type=["txt", "csv", "dxf"], key="upload_b2")
            if file_b2 is not None:
                df_b2_normalized = process_surface_upload(file_b2, "b2")
                if df_b2_normalized is not None:
                    st.write("📊 Xem trước dữ liệu mẫu Bề mặt 2:")
                    st.dataframe(df_b2_normalized.head(10), use_container_width=True)
                    st.session_state.bm2_df = df_b2_normalized
                    st.success("Đã nạp số liệu Bề mặt 2 thành công.")
                    
            boundary_mode = st.selectbox("Lựa chọn hình thức ranh:", ["Mặt bằng hiện hữu", "Ranh giới ấn định", "Tổng hợp Bề mặt 1&2", "Xác định riêng Bề mặt 1,2"], key="bm_mode_2")
            if boundary_mode == "Ranh giới ấn định":
                file_ranh = st.file_uploader("Tải file Ranh giới ấn định ngoài:", type=["txt", "csv", "dxf"], key="ranh_ad_2")
                if file_ranh is not None:
                    st.session_state.ranh_an_dinh_df = process_surface_upload(file_ranh, "rad2")

        st.subheader("📊 Khung Tổng Quan Các Boundary (Overview)")
        bm1_pts = st.session_state.bm1_df[['X', 'Y']].values
        hull_b1 = compute_convex_hull(bm1_pts)
        len_b1 = len(hull_b1) - 1
        
        len_rad = len(compute_convex_hull(st.session_state.ranh_an_dinh_df[['X', 'Y']].values)) - 1 if st.session_state.ranh_an_dinh_df is not None else 0
        len_b2 = len(compute_convex_hull(st.session_state.bm2_df[['X', 'Y']].values)) - 1 if st.session_state.bm2_df is not None else 0
        len_white = len(compute_convex_hull(np.vstack([bm1_pts, st.session_state.bm2_df[['X', 'Y']].values]))) - 1 if st.session_state.bm2_df is not None else 0

        ov_c1, ov_c2, ov_c3, ov_c4 = st.columns(4)
        with ov_c1: st.metric(label="🔴 Ranh ấn định", value=f"{len_rad} Đỉnh", delta="Sẵn sàng" if len_rad > 0 else "Trống", delta_color="normal" if len_rad > 0 else "inverse")
        with ov_c2: st.metric(label="🟢 Ranh Bề mặt 1", value=f"{len_b1} Đỉnh", delta="Sẵn sàng")
        with ov_c3: st.metric(label="🔵 Ranh Bề mặt 2", value=f"{len_b2} Đỉnh", delta="Sẵn sàng" if len_b2 > 0 else "Trống", delta_color="normal" if len_b2 > 0 else "inverse")
        with ov_c4: st.metric(label="⚪ Ranh Tổng hợp", value=f"{len_white} Đỉnh", delta="Hợp nhất" if len_white > 0 else "Chờ BM2", delta_color="normal" if len_white > 0 else "off")

        st.markdown("---")
        
        st.subheader("🏁 [KẾT THÚC] Chế độ hiển thị Boundary")
        
        # --- kHung 1: overview (Không gian hình học địa hình 3D tổng quan) ---
        st.markdown("#### 🌐 kHung 1: Overview (Địa hình 3D)")
        fig_ov = go.Figure()
        fig_ov.add_trace(go.Scatter3d(x=st.session_state.bm1_df['X'], y=st.session_state.bm1_df['Y'], z=st.session_state.bm1_df['Z'], mode='markers', marker=dict(size=2, color='cyan', opacity=0.8), name='Mặt bằng 1'))
        
        if "2." in pa_tinh and st.session_state.bm2_df is not None:
            fig_ov.add_trace(go.Scatter3d(x=st.session_state.bm2_df['X'], y=st.session_state.bm2_df['Y'], z=st.session_state.bm2_df['Z'], mode='markers', marker=dict(size=2, color='magenta', opacity=0.8), name='Mặt bằng 2'))
        elif "1." in pa_tinh:
            x_m = np.linspace(st.session_state.bm1_df['X'].min(), st.session_state.bm1_df['X'].max(), 2)
            y_m = np.linspace(st.session_state.bm1_df['Y'].min(), st.session_state.bm1_df['Y'].max(), 2)
            X_g, Y_g = np.meshgrid(x_m, y_m)
            fig_ov.add_trace(go.Surface(x=X_g, y=Y_g, z=np.full(X_g.shape, z_design), opacity=0.25, showscale=False, name='Thiết kế'))
            
        fig_ov.update_layout(margin=dict(l=0, r=0, b=0, t=10), height=380, showlegend=False)
        st.plotly_chart(fig_ov, use_container_width=True, config={'responsive': True}, key="chart_overview")
        
        # --- khung 2: focus (Tập trung đường bao đỉnh gốc theo đúng màu sắc quy chuẩn) ---
        st.markdown("#### 🎯 khung 2: Focus (Hệ đường bao ranh giới đỉnh gốc)")
        fig_fc = go.Figure()
        
        if boundary_mode == "Mặt bằng hiện hữu":
            fig_fc.add_trace(go.Scatter(x=hull_b1[:, 0], y=hull_b1[:, 1], mode='lines+markers', line=dict(color='green', width=4), name='🟢 Ranh BM1'))
        elif boundary_mode == "Ranh giới ấn định" and st.session_state.ranh_an_dinh_df is not None:
            rad_pts = st.session_state.ranh_an_dinh_df[['X', 'Y']].values
            hull_rad = compute_convex_hull(rad_pts)
            fig_fc.add_trace(go.Scatter(x=hull_rad[:, 0], y=hull_rad[:, 1], mode='lines+markers', line=dict(color='red', width=4), name='🔴 Ranh ấn định'))
        elif boundary_mode == "Tổng hợp Bề mặt 1&2" and st.session_state.bm2_df is not None:
            bm2_pts = st.session_state.bm2_df[['X', 'Y']].values
            hull_white = compute_convex_hull(np.vstack([bm1_pts, bm2_pts]))
            fig_fc.add_trace(go.Scatter(x=hull_white[:, 0], y=hull_white[:, 1], mode='lines+markers', line=dict(color='white', width=4), name='⚪ Ranh tổng hợp'))
        elif boundary_mode == "Xác định riêng Bề mặt 1,2" and st.session_state.bm2_df is not None:
            bm2_pts = st.session_state.bm2_df[['X', 'Y']].values
            hull_b2 = compute_convex_hull(bm2_pts)
            fig_fc.add_trace(go.Scatter(x=hull_b1[:, 0], y=hull_b1[:, 1], mode='lines+markers', line=dict(color='green', width=3), name='🟢 Ranh BM1'))
            fig_fc.add_trace(go.Scatter(x=hull_b2[:, 0], y=hull_b2[:, 1], mode='lines+markers', line=dict(color='blue', width=3), name='🔵 Ranh BM2'))
            
        fig_fc.update_layout(
            margin=dict(l=10, r=10, b=10, t=10), 
            height=380, 
            xaxis=dict(showgrid=True), 
            yaxis=dict(showgrid=True, scaleanchor="x", scaleratio=1),
            legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5, font=dict(size=9))
        )
        st.plotly_chart(fig_fc, use_container_width=True, config={'responsive': True}, key="chart_focus")
        
else:
    st.header("🧱 Phân rã cấu trúc các module tiếp theo (Bước 3 - 5)")
