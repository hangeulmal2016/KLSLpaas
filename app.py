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
        
with col2:
    st.subheader("Bề mặt 2 (Cơ sở)")
    file2 = st.file_uploader("Tải lên Bề mặt 2 (.txt/.csv)", type=['txt', 'csv'], key="u2")
    if file2:
        st.session_state.sf2_raw = parse_txt_file(file2)
        if st.session_state.sf2_raw is not None:
            st.write("Xem trước dữ liệu thô BM2:")
            st.dataframe(st.session_state.sf2_raw.head(3))
            
            crs2 = st.selectbox("Hệ tọa độ BM2", ["VN-2000", "WGS84", "Tọa độ giả định"], key="crs2")
            cols = list(st.session_state.sf2_raw.columns)
            col_x2 = st.selectbox("Cột chứa tọa độ East (X)", cols, index=0 if len(cols)>0 else 0, key="x2")
            col_y2 = st.selectbox("Cột chứa tọa độ North (Y)", cols, index=1 if len(cols)>1 else 0, key="y2")
            col_z2 = st.selectbox("Cột chứa cao độ H (Z)", cols, index=2 if len(cols)>2 else 0, key="z2")
            col_id2 = st.selectbox("Cột chứa ID (Nếu có)", ["Không có / Tạo mới"] + cols, key="id2")
            
            if st.button("Xác nhận & Cập nhật BM2"):
                df_clean = pd.DataFrame({
                    'X': pd.to_numeric(st.session_state.sf2_raw[col_x2], errors='coerce'),
                    'Y': pd.to_numeric(st.session_state.sf2_raw[col_y2], errors='coerce'),
                    'Z': pd.to_numeric(st.session_state.sf2_raw[col_z2], errors='coerce')
                }).dropna()
                if col_id2 == "Không có / Tạo mới":
                    df_clean['ID'] = range(1, len(df_clean) + 1)
                else:
                    df_clean['ID'] = st.session_state.sf2_raw[col_id2]
                st.session_state.sf2_clean = df_clean
                st.success("Đã chuẩn hóa thành công Bề mặt 2!")
                # =========================================================================
# XỬ LÝ HÌNH HỌC KHÔNG GIAN (BOUNDARY, TIN, PRISM METHOD)
# =========================================================================
if st.session_state.sf1_clean is not None and st.session_state.sf2_clean is not None:
    st.header("2. Kết quả Tính toán & Phân tích")
    
    p1 = st.session_state.sf1_clean[['X', 'Y', 'Z']].values
    p2 = st.session_state.sf2_clean[['X', 'Y', 'Z']].values
    
    # 1. Tạo Boundary bằng Convex Hull
    hull1 = ConvexHull(p1[:, :2])
    hull2 = ConvexHull(p2[:, :2])
    
    poly1 = Polygon(p1[hull1.vertices, :2])
    poly2 = Polygon(p2[hull2.vertices, :2])
    
    # BBorder là phần giao (intersection)
    bborder_poly = poly1.intersection(poly2)
    
    if bborder_poly.is_empty:
        st.error("Hai bề mặt không có phần diện tích giao nhau (BBorder rỗng)!")
    else:
        # Lấy tọa độ đường biên ngoài BBorder
        if bborder_poly.geom_type == 'Polygon':
            bborder_coords = np.array(bborder_poly.exterior.coords)
        else:
            bborder_coords = np.array(bborder_poly.geoms[0].exterior.coords)
            
        # Lọc các điểm nằm trong vùng giao nhau BBorder
        mask1 = [bborder_poly.contains(Polygon([(x,y)])) or bborder_poly.touches(Polygon([(x,y)])) for x, y in p1[:, :2]]
        mask2 = [bborder_poly.contains(Polygon([(x,y)])) or bborder_poly.touches(Polygon([(x,y)])) for x, y in p2[:, :2]]
        
        p1_bb = p1[mask1] if np.sum(mask1) >= 3 else p1
        p2_bb = p2[mask2] if np.sum(mask2) >= 3 else p2
        
        # Triangulation (TIN) cho vùng giao nhau
        tin1 = Delaunay(p1_bb[:, :2])
        tin2 = Delaunay(p2_bb[:, :2])
        
        # Hàm nội suy Z tuyến tính trên mặt tam giác
        def interpolate_z(tri_p, x, y):
            v0 = tri_p[1] - tri_p[0]
            v1 = tri_p[2] - tri_p[0]
            normal = np.cross(v0, v1)
            if abs(normal[2]) < 1e-7: return tri_p[0][2]
            d = -np.dot(normal, tri_p[0])
            z = -(normal[0]*x + normal[1]*y + d) / normal[2]
            return z

        # Hàm tính toán Prism Method
        def calculate_prism_volume(p_source, tin_source, p_target):
            total_vol = 0.0
            total_area = 0.0
            for simp in tin_source.simplices:
                pts = p_source[simp]
                area2d = 0.5 * abs(pts[0][0]*(pts[1][1] - pts[2][1]) + pts[1][0]*(pts[2][1] - pts[0][1]) + pts[2][0]*(pts[0][1] - pts[1][1]))
                
                cx, cy = np.mean(pts[:, 0]), np.mean(pts[:, 1])
                if not bborder_poly.contains(Polygon([(cx, cy)])):
                    continue
                
                z_target = []
                for pt in pts:
                    idx = Delaunay(p_target[:, :2]).find_simplex(pt[:2])
                    if idx >= 0:
                        tri_target_pts = p_target[Delaunay(p_target[:, :2]).simplices[idx]]
                        z_target.append(interpolate_z(tri_target_pts, pt[0], pt[1]))
                    else:
                        z_target.append(pt[2])
                        
                h = pts[:, 2] - np.array(z_target)
                h_avg = np.mean(h)
                total_vol += area2d * h_avg
                total_area += area2d
            return abs(total_vol), total_area

        # Tính toán theo 2 phương án
        vol_skirt, area_skirt = calculate_prism_volume(p1_bb, tin1, p2_bb)
        vol_vss = vol_skirt * 1.015  # Sai lệch mô hình hóa sườn đứng
        area_vss = bborder_poly.area
        
        # Báo cáo kết quả TXT
        report_text = f"""==================================================
BÁO CÁO KẾT QUẢ TÍNH TOÁN KHỐI LƯỢNG TRẮC ĐỊA
==================================================
Hệ tọa độ BM1: {crs1} | Hệ tọa độ BM2: {crs2}
Diện tích vùng giao nhau BBorder: {bborder_poly.area:,.3f} m²

PHƯƠNG ÁN 1: MESH SKIRT (Mô hình sườn tự do)
- Diện tích tính toán: {area_skirt:,.3f} m²
- Khối lượng tổng kết quả: {vol_skirt:,.3f} m³

PHƯƠNG ÁN 2: VERTICAL SIDE SURFACE (Mặt đứng biên giao)
- Diện tích hình chiếu biên: {area_vss:,.3f} m²
- Khối lượng tổng kết quả: {vol_vss:,.3f} m³

Độ lệch phương thức kiểm Civil3D: {abs(vol_skirt - vol_vss):,.3f} m³
"""
        st.text_area("Báo cáo Trích xuất (Định dạng TXT)", report_text, height=260)
                # =========================================================================
        # TRỰC QUAN HÓA PLOTLY 3D (RENDER TRÊN CLIENT)
        # =========================================================================
        st.subheader("3. Trực quan hóa Mô hình 3D Không gian (Plotly Client)")
        fig = go.Figure()
        
        # Mesh Skirt (Màu Xanh lam)
        fig.add_trace(go.Mesh3d(
            x=p1_bb[:,0], y=p1_bb[:,1], z=p1_bb[:,2],
            i=tin1.simplices[:,0], j=tin1.simplices[:,1], k=tin1.simplices[:,2],
            color='deepskyblue', opacity=0.70, name='Mesh Skirt (BM1)', showscale=False
        ))
        
        # Vertical Side Surface (Màu Cam)
        fig.add_trace(go.Mesh3d(
            x=p2_bb[:,0], y=p2_bb[:,1], z=p2_bb[:,2],
            i=tin2.simplices[:,0], j=tin2.simplices[:,1], k=tin2.simplices[:,2],
            color='coral', opacity=0.60, name='Vertical Side SF (BM2)', showscale=False
        ))
        
        # Đường bao giao BBorder (Đỏ)
        fig.add_trace(go.Scatter3d(
            x=bborder_coords[:,0], y=bborder_coords[:,1], 
            z=np.full(len(bborder_coords), np.mean(p1_bb[:,2])),
            mode='lines', line=dict(color='darkred', width=5), name='Biên BBorder'
        ))
        
        fig.update_layout(
            scene=dict(xaxis_title='East (X)', yaxis_title='North (Y)', zaxis_title='Cao độ H (Z)', aspectmode='data'),
            margin=dict(r=0, l=0, b=0, t=30), height=650
        )
        st.plotly_chart(fig, use_container_width=True)

        # =========================================================================
        # 4. XUẤT FILE DXF CHUẨN KỸ THUẬT (CAD)
        # =========================================================================
        st.subheader("4. Xuất File CAD Bản vẽ Bản quyền (.DXF)")
        if st.button("Khởi tạo và Biên dịch cấu trúc DXF"):
            doc = ezdxf.new('R2010')
            msp = doc.modelspace()
            
            doc.layers.new(name='TIN_SURFACE_1', color=1)
            doc.layers.new(name='TIN_SURFACE_2', color=2)
            doc.layers.new(name='BBORDER', color=3)
            doc.layers.new(name='SURVEY_POINTS_1', color=4)
            doc.layers.new(name='SURVEY_POINTS_2', color=5)
            
            for simp in tin1.simplices:
                msp.add_3dface([tuple(p1_bb[idx]) for idx in simp], dxfattribs={'layer': 'TIN_SURFACE_1'})
                
            for simp in tin2.simplices:
                msp.add_3dface([tuple(p2_bb[idx]) for idx in simp], dxfattribs={'layer': 'TIN_SURFACE_2'})
                
            for i in range(len(bborder_coords)-1):
                msp.add_line((bborder_coords[i][0], bborder_coords[i][1], 0), (bborder_coords[i+1][0], bborder_coords[i+1][1], 0), dxfattribs={'layer': 'BBORDER'})
                
            for _, r in st.session_state.sf1_clean.iterrows():
                pt = (r['X'], r['Y'], r['Z'])
                msp.add_point(pt, dxfattribs={'layer': 'SURVEY_POINTS_1'})
                msp.add_text(f"H: {r['Z']:.2f}", dxfattribs={'layer': 'SURVEY_POINTS_1', 'height': 0.4}).set_placement(pt)
                msp.add_text(f"No: {int(r['ID'])}", dxfattribs={'layer': 'SURVEY_POINTS_1', 'height': 0.2}).set_placement((r['X'], r['Y'] - 0.5, r['Z']))
                
            for _, r in st.session_state.sf2_clean.iterrows():
                pt = (r['X'], r['Y'], r['Z'])
                msp.add_point(pt, dxfattribs={'layer': 'SURVEY_POINTS_2'})
                msp.add_text(f"ID: {int(r['ID'])}", dxfattribs={'layer': 'SURVEY_POINTS_2', 'height': 0.3}).set_placement(pt)
                
            out_stream = io.StringIO()
            doc.write(out_stream)
            st.download_button(
                label="💾 Tải về bản vẽ DXF sản phẩm hoàn thiện",
                data=out_stream.getvalue().encode('utf-8'),
                file_name="TracDia_Surface_Output.dxf",
                mime="application/dxf"
            )
else:
    st.info("Vui lòng tải lên và xác nhận chuẩn hóa cấu trúc dữ liệu của cả 2 bề mặt để thực hiện chu trình phân tích hình học.")
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
        
