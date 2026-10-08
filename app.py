import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.spatial import ConvexHull
import io

# Cấu hình trang Streamlit
st.set_page_config(page_title="Geodesy Data Processor", layout="wide")
st.title("🗺️ Web App Xử Lý Số Liệu Trắc Địa - Phương Án 1")

# Khởi tạo session state để lưu trữ dữ liệu qua các bước
if 'df_surface1' not in st.session_state:
    st.session_state.df_surface1 = None
if 'hull_surface1' not in st.session_state:
    st.session_state.hull_surface1 = None

# ==========================================
# [BƯỚC 1] XÁC LẬP BỀ MẶT TÍNH TOÁN (BỀ MẶT 1)
# ==========================================
st.header("Trình tự Bước 1: Xác lập Bề mặt 1")

uploaded_file = st.file_saver = st.file_uploader("Tải lên file Mặt bằng hiện hữu (Chấp nhận tạm thời .txt/.csv để demo)", type=["txt", "csv"])

if uploaded_file is not None:
    # Đọc dữ liệu thô
    raw_df = pd.read_csv(uploaded_file)
    st.subheader("Dữ liệu thô vừa tải lên:")
    st.dataframe(raw_df.head())
    
    # Tự động nhận dạng hệ tọa độ (Giả lập logic nhận dạng)
    detected_crs = "VN2000" if "X" in raw_df.columns or "N" in raw_df.columns else "WGS84"
    st.info(f"🔍 Hệ tọa độ tự động nhận dạng: **{detected_crs}**")
    
    # Xác nhận thủ công các cột
    st.markdown("### Xác nhận thủ công cấu trúc cột (Heading):")
    col_id = st.selectbox("Cột số thứ tự (ID):", ["Tự động thêm"] + list(raw_df.columns))
    col_x = st.selectbox("Cột tọa độ X (North):", list(raw_df.columns), index=min(0, len(raw_df.columns)-1))
    col_y = st.selectbox("Cột tọa độ Y (East):", list(raw_df.columns), index=min(1, len(raw_df.columns)-1))
    col_z = st.selectbox("Cột cao độ Z (H):", list(raw_df.columns), index=min(2, len(raw_df.columns)-1))
    
    if st.button("Chuẩn hóa & Cập nhật tập điểm"):
        df = pd.DataFrame()
        
        # Xử lý ID
        if col_id == "Tự động thêm":
            df['ID'] = range(1, len(raw_df) + 1)
        else:
            df['ID'] = raw_df[col_id]
            
        df['X'] = raw_df[col_x]
        df['Y'] = raw_df[col_y]
        df['Z'] = raw_df[col_z]
        
        st.session_state.df_surface1 = df
        st.success("Cập nhật tập điểm Bề mặt 1 thành công!")

# Hiển thị kết quả xử lý Bề mặt 1
if st.session_state.df_surface1 is not None:
    df = st.session_state.df_surface1
    
    # Tính toán Convex Hull (Boundary)
    points_2d = df[['X', 'Y']].values
    if len(points_2d) >= 3:
        hull = ConvexHull(points_2d)
        st.session_state.hull_surface1 = hull
        st.success("⚡ Đã tự động xây dựng Boundary (Convex Hull) cho Bề mặt 1.")
    
    # Tạo layout 2 cột: 1 bên là bảng số liệu, 1 bên là biểu đồ 3D
    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown("**Bảng điểm chuẩn hóa:**")
        st.dataframe(df)
    with c2:
        st.markdown("**Mô hình trực quan 3D (Plotly Client Render):**")
        fig = go.Figure()
        # Vẽ các điểm Mass Points
        fig.add_trace(go.Scatter3d(
            x=df['X'], y=df['Y'], z=df['Z'],
            mode='markers+text',
            text=df['ID'].astype(str),
            marker=dict(size=4, color=df['Z'], colorscale='Viridis', opacity=0.8),
            name='Mass Points'
        ))
        # Vẽ đường bao Boundary nếu có
        if st.session_state.hull_surface1 is not None:
            hull_pts = points_2d[st.session_state.hull_surface1.vertices]
            # Đóng kín vòng đường bao
            hull_pts = np.vstack([hull_pts, hull_pts[0]])
            # Giả lập cao độ trung bình cho đường bao hiển thị trực quan
            z_hull = np.full(len(hull_pts), df['Z'].mean())
            
            fig.add_trace(go.Scatter3d(
                x=hull_pts[:, 0], y=hull_pts[:, 1], z=z_hull,
                mode='lines',
                line=dict(color='green', width=5),
                name='Boundary (Green)'
            ))
            
        fig.update_layout(margin=dict(l=0, r=0, b=0, t=0), scene=dict(aspectmode='data'))
        st.plotly_chart(fig, use_container_width=True)

# ==========================================
# [BƯỚC 2] XÂY DỰNG BOUNDARY TỔNG QUÁT
# ==========================================
st.divider()
st.header("Trình tự Bước 2: Xây dựng Boundary tổng quát")

calc_option = st.radio(
    "Chọn phương án tính toán toán học:",
    ("1. Tính theo Cao độ thiết kế", "2. Tính so với Mặt bằng cơ sở (Bề mặt 2)")
)

if calc_option == "1. Tính theo Cao độ thiết kế":
    design_h = st.number_input("Nhập giá trị cao độ thiết kế (m):", value=0.0)
    boundary_type = st.selectbox(
        "Lựa chọn hình thức xác định ranh:",
        ["Mặt bằng hiện hữu (Sử dụng Boundary của Bề mặt 1)", "Ranh giới ấn định (Tải file ranh riêng)"]
    )
    st.caption(f"Hệ thống sẽ tính toán khối lượng đào/đắp từ Bề mặt 1 xuống/lên cao độ phẳng {design_h}m trong phạm vi ranh đã chọn.")

else:
    st.markdown("### Thiết lập Bề mặt cơ sở (Bề mặt 2)")
    st.info("Quy trình thiết lập Bề mặt 2 diễn ra tương tự như Bề mặt 1 (Tải file ➡️ Nhận dạng ➡️ Xuất Convex Hull).")
    boundary_type_2 = st.selectbox(
        "Lựa chọn hình thức xác định ranh cho Bề mặt 2:",
        ["Mặt bằng hiện hữu", "Ranh giới ấn định", "Tổng hợp Bề mặt 1&2 (Hợp nhất ranh)", "Xác định riêng Bề mặt 1,2"]
    )
