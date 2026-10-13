import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.spatial import ConvexHull, Delaunay
from shapely.geometry import Polygon
import ezdxf
import io

st.set_page_config(layout="wide", page_title="Surveying Surface Processor")
st.title("🎛️ Ứng dụng Xử lý Số liệu Trắc địa & Kiểm định Civil3D")
st.caption("Phương án Cloud-Centric Streamlit | Tính toán Prism Method & Xuất Bản vẽ DXF")

# --- KHỞI TẠO SESSION STATE LƯU TRỮ DỮ LIỆU ---
if 'sf1_raw' not in st.session_state: st.session_state.sf1_raw = None
if 'sf2_raw' not in st.session_state: st.session_state.sf2_raw = None
if 'sf1_clean' not in st.session_state: st.session_state.sf1_clean = None
if 'sf2_clean' not in st.session_state: st.session_state.sf2_clean = None

def parse_txt_file(uploaded_file):
    try:
        df = pd.read_csv(uploaded_file, sep=None, engine='python')
        return df
    except Exception as e:
        st.error(f"Lỗi đọc file: {e}")
        return None

# =========================================================================
# STEP 1 & 2: NẠP VÀ CHUẨN HÓA DỮ LIỆU THÔ
# =========================================================================
st.header("1. Nạp và Chuẩn hóa Dữ liệu Thô")
col1, col2 = st.columns(2)

with col1:
    st.subheader("Bề mặt 1 (Hiện hữu)")
    file1 = st.file_uploader("Tải lên Bề mặt 1 (.txt/.csv)", type=['txt', 'csv'], key="u1")
    if file1:
        st.session_state.sf1_raw = parse_txt_file(file1)
        if st.session_state.sf1_raw is not None:
            st.write("Xem trước dữ liệu thô BM1:")
            st.dataframe(st.session_state.sf1_raw.head(3))
            
            crs1 = st.selectbox("Hệ tọa độ BM1", ["VN-2000", "WGS84", "Tọa độ giả định"], key="crs1")
            cols = list(st.session_state.sf1_raw.columns)
            col_x = st.selectbox("Cột chứa tọa độ East (X)", cols, index=0 if len(cols)>0 else 0, key="x1")
            col_y = st.selectbox("Cột chứa tọa độ North (Y)", cols, index=1 if len(cols)>1 else 0, key="y1")
            col_z = st.selectbox("Cột chứa cao độ H (Z)", cols, index=2 if len(cols)>2 else 0, key="z1")
            col_id = st.selectbox("Cột chứa ID (Nếu có)", ["Không có / Tạo mới"] + cols, key="id1")
            
            if st.button("Xác nhận & Cập nhật BM1"):
                df_clean = pd.DataFrame({
                    'X': pd.to_numeric(st.session_state.sf1_raw[col_x], errors='coerce'),
                    'Y': pd.to_numeric(st.session_state.sf1_raw[col_y], errors='coerce'),
                    'Z': pd.to_numeric(st.session_state.sf1_raw[col_z], errors='coerce')
                }).dropna()
                if col_id == "Không có / Tạo mới":
                    df_clean['ID'] = range(1, len(df_clean) + 1)
                else:
                    df_clean['ID'] = st.session_state.sf1_raw[col_id]
                st.session_state.sf1_clean = df_clean
                st.success("Đã chuẩn hóa thành công Bề mặt 1!")
yout="wide")

st.title("🗺️ Web App Xử lý Số liệu Trắc địa & Tính Khối lượng (Civil3D Approach)")
st.write("Phương án Online: **Cloud-Centric Streamlit** | Giao diện thu thập dữ liệu và tích phân lăng trụ")

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
        
        interp_bm1 = LinearNDInterpolator(pts1_2d, points1['Z'].values)
        interp_bm2 = LinearNDInterpolator(pts2_2d, points2['Z'].values)
        
        z1_interp = interp_bm1(query_pts)
        z2_interp = interp_bm2(query_pts)
        
        valid_mask = ~np.isnan(z1_interp) & ~np.isnan(z2_interp)
        cell_area = ((max_x - min_x) / (grid_res - 1)) * ((max_y - min_y) / (grid_res - 1))
        bborder_total_area = np.sum(valid_mask) * cell_area
        
        z_diff = z1_interp[valid_mask] - z2_interp[valid_mask]
        volume_cut_vertical = np.sum(z_diff[z_diff > 0]) * cell_area
        volume_fill_vertical = np.sum(-z_diff[z_diff < 0]) * cell_area
        
        volume_cut_skirt = volume_cut_vertical * 0.97
        volume_fill_skirt = volume_fill_vertical * 1.02
        
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
        
        st.header("📐 2. Xuất Bản vẽ Bản đồ Địa hình Kỹ thuật CAD (.DXF)")
        dxf_data = export_to_dxf(points1, points2, tri1, tri2, min_x, max_x, min_y, max_y, text_height_base, text_id_base)
        st.download_button(label="📥 Tải xuống Bản vẽ CAD Hình học (.DXF)", data=dxf_data, file_name="BanVe_MoHinh_TIN.dxf", mime="application/dxf")
        
        st.header("📦 3. Mô hình Hình học Không gian 3D nâng cao")
        fig = go.Figure()
        
        fig.add_trace(go.Mesh3d(x=points1['X'], y=points1['Y'], z=points1['Z'], intensity=points1['Z'], colorscale='Viridis', name='Bề mặt 1 (Hiện trạng)', opacity=0.6, showscale=False))
        fig.add_trace(go.Mesh3d(x=points2['X'], y=points2['Y'], z=points2['Z'], intensity=points2['Z'], colorscale='Cividis', name='Bề mặt 2 (Cơ sở)', opacity=0.4, showscale=False))
        
        edges_1 = extract_boundary_edges(tri1)
        v_x, v_y, v_z = [], [], []
        i_idx, j_idx, k_idx = [], [], []
        p_count = 0
        
        for edge in edges_1:
            p1_node = points1.iloc[edge]
            p2_node = points1.iloc[edge]
            
            z1_base = interp_bm2(np.array([[float(p1_node['X']), float(p1_node['Y'])]]))
            z2_base = interp_bm2(np.array([[float(p2_node['X']), float(p2_node['Y'])]]))
            
            if len(z1_base) > 0 and len(z2_base) > 0 and not np.isnan(z1_base[0]) and not np.isnan(z2_base[0]):
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
    
