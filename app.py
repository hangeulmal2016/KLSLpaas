import streamlit as st
import pandas as pd
import numpy as np
from scipy.spatial import Delaunay, ConvexHull
from shapely.geometry import Polygon
import plotly.graph_objects as go
import io
import ezdxf

# Cấu hình giao diện Streamlit rộng hiển thị trực quan
st.set_page_config(page_title="Civil3D Surface Method Validator", layout="wide")
st.title("🛸 Civil3D Method Validator - Trắc địa Web App")
st.markdown("Kiểm tra phương thức biên Civil3D sử dụng cặp biên kép **$BBorder_1$ & $BBorder_2$ (Mesh Skirt 2)**")

# Khởi tạo Session State lưu trữ dữ liệu trắc địa
if 'surf1_data' not in st.session_state: st.session_state['surf1_data'] = None
if 'surf2_data' not in st.session_state: st.session_state['surf2_data'] = None

# Hàm đọc và xử lý file dữ liệu thô (TXT/CSV)
def parse_raw_file(uploaded_file):
    if uploaded_file is None: return None
    bytes_data = uploaded_file.getvalue()
    string_data = bytes_data.decode("utf-8")
    lines = [line.strip() for line in string_data.split("\n") if line.strip()]
    
    data_matrix = []
    for line in lines:
        if ',' in line:
            parts = line.split(',')
        else:
            parts = line.split()
        try:
            data_matrix.append([float(x) for x in parts if x.strip()])
        except ValueError:
            continue
            
    return pd.DataFrame(data_matrix)

# Hàm nội suy cao độ IDW (Inverse Distance Weighting) để gán Z cho biên rời rạc
def interpolate_z(x, y, surf_df):
    dists = np.hypot(surf_df['X'] - x, surf_df['Y'] - y)
    idx_min = np.argmin(dists)
    if dists[idx_min] < 1e-3: 
        return surf_df['Z'].iloc[idx_min]
    idx_neighbors = np.argsort(dists)[:3]
    weights = 1.0 / (dists.iloc[idx_neighbors].values + 1e-6)
    return np.sum(surf_df['Z'].iloc[idx_neighbors].values * weights) / np.sum(weights)

# Tính diện tích hình chiếu 2D của tam giác từ tọa độ đỉnh phẳng
def tri_area_2d(p1, p2, p3):
    return 0.5 * abs(p1[0]*(p2[1] - p3[1]) + p2[0]*(p3[1] - p1[1]) + p3[0]*(p1[1] - p2[1]))
    # --- GIAO DIỆN KHU VỰC TẢI DỮ LIỆU ---
col_up1, col_up2 = st.columns(2)
with col_up1:
    st.subheader("📁 Bề mặt 1 (Hiện hữu / Top Surface)")
    file1 = st.file_uploader("Tải lên file BM1 (TXT/CSV)", type=["txt", "csv"], key="f1")
    if file1:
        df1_raw = parse_raw_file(file1)
        if df1_raw is not None: st.write("Dữ liệu thô BM1 (Xem trước):", df1_raw.head(3))

with col_up2:
    st.subheader("📁 Bề mặt 2 (Cơ sở / Datum Surface)")
    file2 = st.file_uploader("Tải lên file BM2 (TXT/CSV)", type=["txt", "csv"], key="f2")
    if file2:
        df2_raw = parse_raw_file(file2)
        if df2_raw is not None: st.write("Dữ liệu thô BM2 (Xem trước):", df2_raw.head(3))

# --- KHU VỰC CHUẨN HÓA TOẠ ĐỘ & ĐÁNH ID ---
if file1 and file2:
    st.header("⚙️ Chuẩn hóa cấu trúc đồ họa CAD & Hệ tọa độ")
    crs_option = st.selectbox("Hệ tọa độ nhận dạng", ["VN-2000", "WGS84", "Tọa độ giả định"])
    
    # Thanh trượt tùy biến Step Offset tinh chỉnh độ mịn vách ảo
    stepoffset = st.slider("Cấu hình bước lệch biên Step Offset (mét)", min_value=0.0001, max_value=0.05, value=0.001, step=0.0001, format="%.4f")
    
    col_map1, col_map2 = st.columns(2)
    with col_map1:
        st.markdown("**Định cấu hình cột cho BM1:**")
        cols1 = list(df1_raw.columns)
        x_col1 = st.selectbox("Cột East (X)", cols1, index=min(0, len(cols1)-1), key="x1")
        y_col1 = st.selectbox("Cột North (Y)", cols1, index=min(1, len(cols1)-1), key="y1")
        z_col1 = st.selectbox("Cột Cao độ (H/Z)", cols1, index=min(2, len(cols1)-1), key="z1")
        id_col1 = st.selectbox("Cột ID (Nếu có)", ["Không có"] + cols1, index=0, key="id1")
        
        if st.button("Xác nhận & Cập nhật dữ liệu BM1"):
            df_cleaned = pd.DataFrame({'X': df1_raw[x_col1].values, 'Y': df1_raw[y_col1].values, 'Z': df1_raw[z_col1].values})
            df_cleaned['ID'] = df1_raw[id_col1].values if id_col1 != "Không có" else np.arange(1, len(df_cleaned) + 1)
            st.session_state['surf1_data'] = df_cleaned
            st.success("Đã đồng bộ thông số hình học BM1!")

    with col_map2:
        st.markdown("**Định cấu hình cột cho BM2:**")
        cols2 = list(df2_raw.columns)
        x_col2 = st.selectbox("Cột East (X)", cols2, index=min(0, len(cols2)-1), key="x2")
        y_col2 = st.selectbox("Cột North (Y)", cols2, index=min(1, len(cols2)-1), key="y2")
        z_col2 = st.selectbox("Cột Cao độ (H/Z)", cols2, index=min(2, len(cols2)-1), key="z2")
        id_col2 = st.selectbox("Cột ID (Nếu có)", ["Không có"] + cols2, index=0, key="id2")
        
        if st.button("Xác nhận & Cập nhật dữ liệu BM2"):
            df_cleaned = pd.DataFrame({'X': df2_raw[x_col2].values, 'Y': df2_raw[y_col2].values, 'Z': df2_raw[z_col2].values})
            df_cleaned['ID'] = df2_raw[id_col2].values if id_col2 != "Không có" else np.arange(1, len(df_cleaned) + 1)
            st.session_state['surf2_data'] = df_cleaned
            st.success("Đã đồng bộ thông số hình học BM2!")
# --- PHÂN TÍCH HÌNH HỌC KHÔNG GIAN KHỐI LƯỢNG ---
if st.session_state['surf1_data'] is not None and st.session_state['surf2_data'] is not None:
    s1 = st.session_state['surf1_data']
    s2 = st.session_state['surf2_data']
    
    # 1. Trích xuất ranh giới đơn bằng Convex Hull
    p1_2d = s1[['X', 'Y']].values
    p2_2d = s2[['X', 'Y']].values
    hull1 = ConvexHull(p1_2d)
    hull2 = ConvexHull(p2_2d)
    
    poly1 = Polygon(p1_2d[hull1.vertices])
    poly2 = Polygon(p2_2d[hull2.vertices])
    
    # Tính giao diện trực giao BBorder lõi
    bborder_poly = poly1.intersection(poly2)
    
    if bborder_poly.is_empty:
        st.error("❌ Không thể thực hiện phép tính hình học: BBorder giữa 2 bề mặt hoàn toàn trống!")
    else:
        # Lọc dữ liệu lõi nằm bên trong BBorder để chạy Delaunay TIN chuẩn xác
        mask1 = [bborder_poly.contains(Polygon([(x,y)])) or bborder_poly.touches(Polygon([(x,y)])) for x, y in zip(s1['X'], s1['Y'])]
        mask2 = [bborder_poly.contains(Polygon([(x,y)])) or bborder_poly.touches(Polygon([(x,y)])) for x, y in zip(s2['X'], s2['Y'])]
        s1_in = s1[mask1].copy()
        s2_in = s2[mask2].copy()
        
        tri1 = Delaunay(s1_in[['X', 'Y']].values)
        tri2 = Delaunay(s2_in[['X', 'Y']].values)
        
        # --- THUẬT TOÁN KÉP: TẠO BBORDER1 & BBORDER2 (MESH SKIRT 2) ---
        bborder_1_poly = bborder_poly.buffer(stepoffset, join_style=2)   # Phóng to cho mặt 1
        bborder_2_poly = bborder_poly.buffer(-stepoffset, join_style=2)  # Thu nhỏ cho mặt 2
        
        coords_1 = np.array(bborder_1_poly.exterior.coords)
        coords_2 = np.array(bborder_2_poly.exterior.coords)
        
        mesh_skirt_2_faces = []
        vol_skirt_2 = 0.0
        
        min_segments = min(len(coords_1), len(coords_2)) - 1
        for i in range(min_segments):
            p1_top, p2_top = coords_1[i], coords_1[i+1]
            p1_bot, p2_bot = coords_2[i], coords_2[i+1]
            
            z1_t = interpolate_z(p1_top[0], p1_top[1], s1_in)
            z2_t = interpolate_z(p2_top[0], p2_top[1], s1_in)
            z1_b = interpolate_z(p1_bot[0], p1_bot[1], s2_in)
            z2_b = interpolate_z(p2_bot[0], p2_bot[1], s2_in)
            
            # Tam giác TIN Alpha (Top1 - Top2 - Bot1)
            t1 = [(p1_top[0], p1_top[1], z1_t), (p2_top[0], p2_top[1], z2_t), (p1_bot[0], p1_bot[1], z1_b)]
            # Tam giác TIN Beta (Top2 - Bot2 - Bot1)
            t2 = [(p2_top[0], p2_top[1], z2_t), (p2_bot[0], p2_bot[1], z2_b), (p1_bot[0], p1_bot[1], z1_b)]
            
            mesh_skirt_2_faces.extend([t1, t2])
            
            # Tính khối lượng lăng trụ đào đắp từng ô lưới (Prism Method)
            a_t1 = tri_area_2d(p1_top, p2_top, p1_bot)
            h_t1 = abs((z1_t + z2_t + z1_b) / 3.0)
            vol_skirt_2 += a_t1 * h_t1
            
            a_t2 = tri_area_2d(p2_top, p2_bot, p1_bot)
            h_t2 = abs((z2_t + z2_b + z1_b) / 3.0)
            vol_skirt_2 += a_t2 * h_t2

        # Tính toán sơ bộ phương án Mesh Skirt 1 (Gốc cũ) để đối chiếu
        area_core = bborder_poly.area
        vol_skirt_1 = abs(s1_in['Z'].mean() - s2_in['Z'].mean()) * area_core

        # --- HIỂN THỊ KẾT QUẢ VĂN BẢN VÀ ĐỒ THỊ ---
        st.header("📊 Kết quả phân tích hình học & Thể tích Lăng trụ")
        report_text = f"""--- BÁO CÁO ĐỐI CHIẾU THUẬT TOÁN BIÊN CIVIL3D ---
Hệ tọa độ trắc địa: {crs_option}
Bước dịch vách đứng (Step Offset): {stepoffset} m
Diện tích lõi tính toán BBorder: {area_core:.3f} m²

[Phương án 1] MESH SKIRT GỐC (Biên xiên chuyển tiếp tự nhiên)
- Diện tích phủ: {area_core:.3f} m²
- Thể tích khối lượng tổng: {vol_skirt_1:.3f} m³

[Phương án 2] MESH SKIRT 2 (Thay thế cho Vertical Side Surface bằng cặp biên kép)
- Diện tích phủ BBorder1 (Mặt 1): {bborder_1_poly.area:.3f} m²
- Diện tích phủ BBorder2 (Mặt 2): {bborder_2_poly.area:.3f} m²
- Thể tích tính toán (Prism Method): {vol_skirt_2:.3f} m³
"""
        st.code(report_text, language="text")
        
        # --- ĐỒ THỊ TRỰC QUAN HÓA TRÊN CLIENT SIDE ---
        st.header("🌐 Trực quan hóa tương tác mô hình 3D (Plotly)")
        fig = go.Figure()
        
        fig.add_trace(go.Mesh3d(x=s1_in['X'], y=s1_in['Y'], z=s1_in['Z'], intensity=s1_in['Z'], colorscale='Viridis', name='TIN Bề mặt 1', showscale=False))
        fig.add_trace(go.Mesh3d(x=s2_in['X'], y=s2_in['Y'], z=s2_in['Z'], intensity=s2_in['Z'], colorscale='Cividis', name='TIN Bề mặt 2', showscale=False))
        
        # Vẽ cấu trúc vách đứng ảo Mesh Skirt 2
        ms2_x, ms2_y, ms2_z = [], [], []
        for face in mesh_skirt_2_faces:
            for pt in face:
                ms2_x.append(pt[0]); ms2_y.append(pt[1]); ms2_z.append(pt[2])
        
        fig.add_trace(go.Mesh3d(x=ms2_x, y=ms2_y, z=ms2_z, color='orange', opacity=0.7, name='Mesh Skirt 2 (Vách đứng)'))
        fig.update_layout(scene=dict(aspectmode='data'), margin=dict(l=0, r=0, b=0, t=40))
        st.plotly_chart(fig, use_container_width=True)
        
        # --- XUẤT FILE DXF CHUẨN CAD ---
        st.header("💾 Xuất bản dữ liệu đồ họa Kỹ thuật (.DXF)")
        
        doc = ezdxf.new('R2010')
        msp = doc.modelspace()
        
        doc.layers.new(name='TIN_SURFACE_1', color=1)
        doc.layers.new(name='TIN_SURFACE_2', color=2)
        doc.layers.new(name='BBORDER', color=3)
        doc.layers.new(name='POINTS_BM1', color=4)
        doc.layers.new(name='POINTS_BM2', color=5)
        
        for t in tri1.simplices:
            pts = s1_in.iloc[t][['X', 'Y', 'Z']].values
            if len(pts) == 3: msp.add_3dface(pts, dxfattribs={'layer': 'TIN_SURFACE_1'})
                
        for t in tri2.simplices:
            pts = s2_in.iloc[t][['X', 'Y', 'Z']].values
            if len(pts) == 3: msp.add_3dface(pts, dxfattribs={'layer': 'TIN_SURFACE_2'})
                
        bb_coords_2d = np.array(bborder_poly.exterior.coords)[:, :2]
        msp.add_lwpolyline(bb_coords_2d, dxfattribs={'layer': 'BBORDER'})
        
        for _, r in s1_in.iterrows():
            msp.add_point((r['X'], r['Y'], r['Z']), dxfattribs={'layer': 'POINTS_BM1'})
            msp.add_text(f"H: {r['Z']:.2f}", dxfattribs={'layer': 'POINTS_BM1', 'height': 0.4}).set_placement((r['X']+0.1, r['Y']+0.1, r['Z']))
            msp.add_text(f"ID: {int(r['ID'])}", dxfattribs={'layer': 'POINTS_BM1', 'height': 0.2}).set_placement((r['X']+0.1, r['Y']-0.2, r['Z']))
            
        for _, r in s2_in.iterrows():
            msp.add_point((r['X'], r['Y'], r['Z']), dxfattribs={'layer': 'POINTS_BM2'})
            msp.add_text(f"ID: {int(r['ID'])}", dxfattribs={'layer': 'POINTS_BM2', 'height': 0.4}).set_placement((r['X']+0.1, r['Y']+0.1, r['Z']))
            
        out_stream = io.StringIO()
        doc.write(out_stream)
        dxf_bytes = out_stream.getvalue().encode('utf-8')
        
        st.download_button(
            label="📥 Tải xuống bản vẽ mặt lưới hoàn chỉnh (.DXF)",
            data=dxf_bytes,
            file_name="Mesh_Skirt_2_Validation.dxf",
            mime="application/dxf"
            )
        
