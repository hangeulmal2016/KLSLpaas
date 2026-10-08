import streamlit as st
import pandas as pd
import numpy as np
from scipy.spatial import ConvexHull
from shapely.geometry import Polygon
import plotly.graph_objects as go
import ezdxf

st.set_page_config(page_title="Trắc Địa Web App", layout="wide")
st.title("Ứng dụng Xử lý Số liệu Trắc địa & Tính Khối lượng")

# Khởi tạo session state để lưu trữ dữ liệu qua các bước
if 'surface_1_df' not in st.session_state:
    st.session_state['surface_1_df'] = None
if 'boundary_1' not in st.session_state:
    st.session_state['boundary_1'] = None

# ==========================================
# [BƯỚC 1] XÁC LẬP BỀ MẶT TÍNH TOÁN (BỀ MẶT 1)
# ==========================================
st.header("Step 1: Xác lập Bề mặt Tính toán (Bề mặt 1)")

uploaded_file = st.file_uploader("Tải lên file Mặt bằng hiện hữu (TX/CSV mẫu)", type=["txt", "csv", "dxf"])

if uploaded_file is not None:
    # --- Đọc và Chuẩn hóa dữ liệu (Giả định file dạng bảng) ---
    df = pd.read_csv(uploaded_file)
    st.subheader("Dữ liệu thô vừa tải lên:")
    st.dataframe(df.head())
    
    # >> Tự động nhận dạng hệ tọa độ (Logic demo đơn giản)
    detected_crs = "WGS84"
    if "X" in df.columns and df["X"].max() > 100000:
        detected_crs = "VN2000"
    st.info(f"Hệ tọa độ tự động nhận dạng: **{detected_crs}**")
    
    # >> Xác nhận thủ công các cột
    st.markdown("##### Xác nhận thủ công các cột dữ liệu:")
    col_x = st.selectbox("Cột trục X (East):", df.columns, index=0 if "X" in df.columns else 0)
    col_y = st.selectbox("Cột trục Y (North):", df.columns, index=1 if "Y" in df.columns else 0)
    col_z = st.selectbox("Cột trục Z (Cao độ H):", df.columns, index=2 if "Z" in df.columns else 0)
    col_id = st.selectbox("Cột ID (Số TT):", ["Tự động thêm"] + list(df.columns))
    
    # >> Xử lý cột ID
    if col_id == "Tự động thêm":
        df['Point_ID'] = range(1, len(df) + 1)
    else:
        df['Point_ID'] = df[col_id]
        
    # Cập nhật tập điểm đã chuẩn hóa vào Session State
    proc_df = df[[col_x, col_y, col_z, 'Point_ID']].copy()
    proc_df.columns = ['X', 'Y', 'Z', 'ID']
    st.session_state['surface_1_df'] = proc_df
    
    # >> Xây dựng Boundary (Convex Hull)
    points = proc_df[['X', 'Y']].values
    if len(points) >= 3:
        hull = ConvexHull(points)
        boundary_points = points[hull.vertices]
        # Đóng kín vòng ranh giới bằng cách nối điểm cuối về điểm đầu
        boundary_points = np.vstack([boundary_points, boundary_points[0]])
        st.session_state['boundary_1'] = boundary_points
        st.success("Xây dựng đường bao Convex Hull thành công cho Bề mặt 1!")

    # --- Render 3D trực quan bằng Plotly ---
    if st.session_state['surface_1_df'] is not None:
        fig = go.Figure()
        # Vẽ tập điểm 3D (Mass points)
        fig.add_trace(go.Scatter3d(
            x=proc_df['X'], y=proc_df['Y'], z=proc_df['Z'],
            mode='markers', marker=dict(size=3, color=proc_df['Z'], colorscale='Viridis'),
            name='Mass Points 1'
        ))
        # Vẽ đường bao 2D chiếu lên cao độ min
        if st.session_state['boundary_1'] is not None:
            min_z = proc_df['Z'].min()
            fig.add_trace(go.Scatter3d(
                x=st.session_state['boundary_1'][:, 0],
                y=st.session_state['boundary_1'][:, 1],
                z=[min_z] * len(st.session_state['boundary_1']),
                mode='lines', line=dict(color='green', width=4),
                name='Boundary 1 (Green)'
            ))
        fig.update_layout(scene=dict(aspectmode='data'), margin=dict(l=0, r=0, b=0, t=40))
        st.plotly_chart(fig, use_container_width=True)

# ==========================================
# [BƯỚC 2] XÂY DỰNG BOUNDARY TỔNG QUÁT
# ==========================================
st.header("Step 2: Xây dựng Boundary Tổng quát")

option_calc = st.radio("Chọn phương án tính toán Khối lượng:", 
                       ["1. Tính theo Cao độ thiết kế", "2. Tính so với Mặt bằng cơ sở"])

if option_calc == "1. Tính theo Cao độ thiết kế":
    design_h = st.number_input("Nhập giá trị cao độ thiết kế (m):", value=0.0)
    ranh_option = st.selectbox("Hình thức xác định ranh:", ["Mặt bằng hiện hữu", "Ranh giới ấn định"])
    
    if ranh_option == "Mặt bằng hiện hữu":
        st.write("Đường bao tổng quát sử dụng **Boundary của Bề mặt 1 (Màu Green)**")
    else:
        st.file_uploader("Tải lên file Ranh giới ấn định (DXF/TXT...)", type=["txt", "csv", "dxf"], key="ranh_an_dinh")

elif option_calc == "2. Tính so với Mặt bằng cơ sở":
    st.subheader("Xác lập Bề mặt 2 (Mặt bằng cơ sở)")
    uploaded_file_2 = st.file_uploader("Tải lên file Bề mặt 2", type=["txt", "csv", "dxf"])
    
    ranh_option_2 = st.selectbox("Hình thức xác định ranh tổng hợp:", 
                                 ["Mặt bằng hiện hữu", "Ranh giới ấn định", "Tổng hợp Bề mặt 1 & 2", "Xác định riêng Bề mặt 1, 2"])
    
    if ranh_option_2 == "Tổng hợp Bề mặt 1 & 2":
        st.info("Hệ thống sẽ chạy thuật toán Hợp nhất (Union) các đa giác Convex Hull của cả 2 bề mặt.")
        # Ví dụ logic: dùng shapely.ops.unary_union([poly1, poly2]) để xuất Boundary tổng hợp màu White.
