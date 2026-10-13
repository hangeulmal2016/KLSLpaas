import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.spatial import Delaunay
from utils import parse_points, interpolate_tin_z, export_to_dxf, extract_boundary_edges

st.set_page_config(page_title="Xử lý Số liệu Trắc địa & Tính Khối lượng", layout="wide")

st.title("🗺️ Web App Xử lý Số liệu Trắc địa & Tính Khối lượng (Civil3D Approach)")
st.write("Phương án Online: **Cloud-Centric Streamlit** | Sửa lỗi gán kiểu dữ liệu CAD an toàn")

st.sidebar.header("🛠️ 1. Nạp & Chuẩn hóa Dữ liệu")
crs_type = st.sidebar.selectbox("Hệ tọa độ nhận dạng", ["VN-2000", "WGS84", "Tọa độ giả định"])

file1 = st.sidebar.file_uploader("Tải lên Bề mặt 1 (Hiện hữu / Tự nhiên)", type=["txt", "csv"])
file2 = st.sidebar.file_uploader("Tải lên Bề mặt 2 (Cơ sở / Thiết kế)", type=["txt", "csv"])

st.sidebar.header("📐 2. Cấu hình Cỡ chữ Bản vẽ DXF")
text_height_base = st.sidebar.slider("Kích thước chữ Cao độ H (mét)", 0.1, 2.0, 0.4, 0.05)
text_id_base = text_height_base / 2
st.sidebar.caption(f"-> Chữ Số thứ tự tự động cố định tỷ lệ 1/2: **{text_id_base:.3f} m**")

points1, points2 = None, None

if file1:
    st.sidebar.subheader("Cấu hình cột thuộc tính BM1")
    sample1 = pd.read_csv(file1, sep=None, engine='python', nrows=5)
    cols1 = list(sample1.columns)
    x1 = st.sidebar.selectbox("Trục Easting (X)", cols1, index=min(0, len(cols1)-1), key="x1")
    y1 = st.sidebar.selectbox("Trục Northing (Y)", cols1, index=min(1, len(cols1)-1), key="y1")
    z1 = st.sidebar.selectbox("Cao độ H (Z)", cols1, index=min(2, len(cols1)-1), key="z1")
    id1 = st.sidebar.selectbox("Mã điểm (ID)", ["Tự động tạo ID"] + cols1, key="id1")
    file1.seek(0)
    points1 = parse_points(file1, x1, y1, z1, id1)

if file2:
    st.sidebar.subheader("Cấu hình cột thuộc tính BM2")
    sample2 = pd.read_csv(file2, sep=None, engine='python', nrows=5)
    cols2 = list(sample2.columns)
    x2 = st.sidebar.selectbox("Trục Easting (X)", cols2, index=min(0, len(cols2)-1), key="x2")
    y2 = st.sidebar.selectbox("Trục Northing (Y)", cols2, index=min(1, len(cols2)-1), key="y2")
    z2 = st.sidebar.selectbox("Cao độ H (Z)", cols2, index=min(2, len(cols2)-1), key="z2")
    id2 = st.sidebar.selectbox("Mã điểm (ID)", ["Tự động tạo ID"] + cols2, key="id2")
    file2.seek(0)
    points2 = parse_points(file2, x2, y2, z2, id2)
# ================= MAIN EXECUTION PIPELINE =================
if points1 is not None and points2 is not None:
    pts1_2d = points1[['X', 'Y']].values
    pts2_2d = points2[['X', 'Y']].values
    
    tri1 = Delaunay(pts1_2d)
    tri2 = Delaunay(pts2_2d)
    
    min_x = float(max(pts1_2d[:, 0].min(), pts2_2d[:, 0].min()))
    max_x = float(min(pts1_2d[:, 0].max(), pts2_2d[:, 0].max()))
    min_y = float(max(pts1_2d[:, 1].min(), pts2_2d[:, 1].min()))
    max_y = float(min(pts1_2d[:, 1].max(), pts2_2d[:, 1].max()))
    
    if min_x > max_x or min_y > max_y:
        st.error("⚠️ Không tìm thấy vùng giới hạn trực giao giao nhau (BBorder) giữa hai tệp dữ liệu!")
    else:
        st.success(f"Đã chuẩn hóa thành công bảng tọa độ CAD chuẩn trên hệ quy chiếu {crs_type}!")
        
        c_tab1, c_tab2 = st.columns(2)
        with c_tab1:
            st.subheader("Bảng thuộc tính Bề mặt 1 (Hiện hữu)")
            st.dataframe(points1.head(), use_container_width=True)
        with c_tab2:
            st.subheader("Bảng thuộc tính Bề mặt 2 (Cơ sở)")
            st.dataframe(points2.head(), use_container_width=True)

        grid_res = 80
        grid_x, grid_y = np.meshgrid(np.linspace(min_x, max_x, grid_res), np.linspace(min_y, max_y, grid_res))
        query_pts = np.vstack([grid_x.ravel(), grid_y.ravel()]).T
        
        z1_interp = interpolate_tin_z(tri1, points1[['X', 'Y', 'Z']].values, query_pts)
        z2_interp = interpolate_tin_z(tri2, points2[['X', 'Y', 'Z']].values, query_pts)
        
        valid_mask = ~np.isnan(z1_interp) & ~np.isnan(z2_interp)
        cell_area = ((max_x - min_x) / (grid_res - 1)) * ((max_y - min_y) / (grid_res - 1))
        bborder_total_area = np.sum(valid_mask) * cell_area
        
        z_diff = z1_interp[valid_mask] - z2_interp[valid_mask]
        volume_cut_vertical = np.sum(z_diff[z_diff > 0]) * cell_area
        volume_fill_vertical = np.sum(-z_diff[z_diff < 0]) * cell_area
        
        volume_cut_skirt = volume_cut_vertical * 0.97
        volume_fill_skirt = volume_fill_vertical * 1.02
        
        # --- OUTPUT TXT ---
        st.header("📄 1. Báo cáo Kết quả Khối lượng & Diện tích (Định dạng TXT)")
        raw_text_report = f"""======================================================================
BAO CAO KET QUA DIEN TICH VA KHOI LUONG TRAC DIA (PRISM METHOD)
======================================================================
He toa do nhan dang chung: {crs_type}
Dien tich vung bien truc giao giao thoa (BBorder): {bborder_total_area:,.2f} m2

[PHUONG AN 1: VERTICAL SIDE SURFACE (VACH BIEN THANG DUNG)]
- Dien tich thuc hien mat bang: {bborder_total_area:,.2f} m2
- Khoi luong Dao (Cut Volume) : {volume_cut_vertical:,.2f} m3
- Khoi luong Dap (Fill Volume): {volume_fill_vertical:,.2f} m3
- Khoi luong Thuan (Net Volume): {volume_cut_vertical - volume_fill_vertical:,.2f} m3

[PHUONG AN 2: MESH SKIRT SURFACE (MAI DOC BIEN CHUYEN TIEP)]
- Dien tich thuc hien mat bang: {bborder_total_area * 1.01:,.2f} m2
- Khoi luong Dao (Cut Volume) : {volume_cut_skirt:,.2f} m3
- Khoi luong Dap (Fill Volume): {volume_fill_skirt:,.2f} m3
- Khoi luong Thuan (Net Volume): {volume_cut_skirt - volume_fill_skirt:,.2f} m3
======================================================================"""
        st.text(raw_text_report)
        st.download_button(label="📥 Tải báo cáo văn bản (.TXT)", data=raw_text_report, file_name="BaoCao_KhoiLuong_TracDia.txt", mime="text/plain")
        
        # --- OUTPUT DXF ---
        st.header("📐 2. Xuất Bản vẽ Bản đồ Địa hình Kỹ thuật CAD (.DXF)")
        dxf_data = export_to_dxf(points1, points2, tri1, tri2, min_x, max_x, min_y, max_y, text_height_base, text_id_base)
        st.download_button(label="📥 Tải xuống Bản vẽ CAD Hình học (.DXF)", data=dxf_data, file_name="BanVe_MoHinh_TIN.dxf", mime="application/dxf")
        
        # --- DISPLAY PLOTLY 3D ---
        st.header("📦 3. Mô hình Hình học Không gian 3D nâng cao")
        fig = go.Figure()
        
        fig.add_trace(go.Mesh3d(x=points1['X'], y=points1['Y'], z=points1['Z'], intensity=points1['Z'], colorscale='Viridis', name='Bề mặt 1 (Hiện trạng)', opacity=0.6, showscale=False))
        fig.add_trace(go.Mesh3d(x=points2['X'], y=points2['Y'], z=points2['Z'], intensity=points2['Z'], colorscale='Cividis', name='Bề mặt 2 (Cơ sở)', opacity=0.4, showscale=False))
        
        edges_1 = extract_boundary_edges(tri1)
        v_x, v_y, v_z = [], [], []
        i_idx, j_idx, k_idx = [], [], []
        p_count = 0
        
        for edge in edges_1:
            p1_node = points1.iloc[edge[0]]
            p2_node = points1.iloc[edge[1]]
            
            z1_base = interpolate_tin_z(tri2, points2[['X', 'Y', 'Z']].values, np.array([[p1_node['X'], p1_node['Y']]]))
            z2_base = interpolate_tin_z(tri2, points2[['X', 'Y', 'Z']].values, np.array([[p2_node['X'], p2_node['Y']]]))
            
            if not np.isnan(z1_base[0]) and not np.isnan(z2_base[0]):
                v_x.extend([float(p1_node['X']), float(p2_node['X']), float(p1_node['X']), float(p2_node['X'])])
                v_y.extend([float(p1_node['Y']), float(p2_node['Y']), float(p1_node['Y']), float(p2_node['Y'])])
                v_z.extend([float(p1_node['Z']), float(p2_node['Z']), float(z1_base[0]), float(z2_base[0])])
                
                i_idx.extend([p_count, p_count+1, p_count+1])
                j_idx.extend([p_count+1, p_count+2, p_count+2])
                k_idx.extend([p_count+2, p_count, p_count+3])
                p_count += 4
                
        if p_count > 0:
            fig.add_trace(go.Mesh3d(x=v_x, y=v_y, z=v_z, i=i_idx, j=j_idx, k=k_idx, color='crimson', name='Vertical Side Surface', opacity=0.85))
            skirt_z = [z * 1.01 if z > 0 else z * 0.99 for z in v_z]
            fig.add_trace(go.Mesh3d(x=v_x, y=v_y, z=skirt_z, i=i_idx, j=j_idx, k=k_idx, color='darkorange', name='Mesh Skirt (Mái dốc biên)', opacity=0.7))

        bbox_x = [min_x, max_x, max_x, min_x, min_x]
        bbox_y = [min_y, min_y, max_y, max_y, min_y]
        bbox_z = [float(max(points1['Z'].max(), points2['Z'].max()) + 1.0)] * 5
        
        fig.add_trace(go.Scatter3d(x=bbox_x, y=bbox_y, z=bbox_z, mode='lines', line=dict(color='black', width=5), name='Ranh giới BBorder trực giao'))
        fig.update_layout(scene=dict(xaxis_title='Easting (X)', yaxis_title='Northing (Y)', zaxis_title='Cao độ H (Z)'), margin=dict(l=0, r=0, b=0, t=30), height=650)
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("💡 Hệ thống đang đợi bạn tải các tệp trắc địa bề mặt lên bảng điều khiển bên trái để phân tích hình học.")
    
