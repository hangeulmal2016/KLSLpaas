import streamlit as st
import pandas as pd
import numpy as np
import re
import io
from scipy.spatial import ConvexHull
from shapely.geometry import Polygon
from shapely.ops import unary_union
import plotly.graph_objects as go
import ezdxf

# --- CẤU HÌNH TRANG WEB STREAMLIT ---
st.set_page_config(page_title="Trắc Địa & Khối Lượng Web App", layout="wide", initial_sidebar_state="expanded")
st.title("🏗️ Ứng dụng Xử lý Số liệu Trắc địa & Tính Khối lượng")
st.markdown("---")

# --- KHỞI TẠO BỘ NHỚ ĐỆM (SESSION STATE) ---
if 'surface_1_df' not in st.session_state: st.session_state['surface_1_df'] = None
if 'boundary_1' not in st.session_state: st.session_state['boundary_1'] = None
if 'surface_1_crs' not in st.session_state: st.session_state['surface_1_crs'] = None

if 'surface_2_df' not in st.session_state: st.session_state['surface_2_df'] = None
if 'boundary_2' not in st.session_state: st.session_state['boundary_2'] = None
if 'surface_2_crs' not in st.session_state: st.session_state['surface_2_crs'] = None

if 'final_boundary_type' not in st.session_state: st.session_state['final_boundary_type'] = None
if 'final_boundaries' not in st.session_state: st.session_state['final_boundaries'] = []  
if 'design_height_value' not in st.session_state: st.session_state['design_height_value'] = 0.0
# --- CÁC HÀM TRỢ NĂNG XỬ LÝ SỐ LIỆU TRẮC ĐỊA ---
def detect_coordinate_system(df, sample_cols):
    """Tự động nhận dạng hệ tọa độ dựa trên dải giá trị dữ liệu số tại Việt Nam"""
    for col in sample_cols:
        try:
            max_val = df[col].max()
            min_val = df[col].min()
            if max_val > 100000:
                return "VN2000"
            if 8.0 <= min_val <= 24.0 and 102.0 <= max_val <= 110.0:
                return "WGS84"
        except:
            continue
    return "Tọa độ giả định"

def suggest_headings(columns):
    """Gợi ý tự động gán tiêu đề cột dựa trên các ký tự viết tắt ngành trắc địa"""
    suggestions = {"E": 0, "N": 0, "Z": 0, "ID": 0}
    for idx, col in enumerate(columns):
        col_lower = str(col).lower().strip()
        if re.search(r'\b(e|east|x)\b', col_lower) or 'east' in col_lower: suggestions["E"] = idx
        elif re.search(r'\b(n|north|y)\b', col_lower) or 'north' in col_lower: suggestions["N"] = idx
        elif re.search(r'\b(z|h|elevation|cao_do|caodo)\b', col_lower): suggestions["Z"] = idx
        elif re.search(r'\b(id|stt|no|name|diem|point)\b', col_lower): suggestions["ID"] = idx
    return suggestions

def compute_convex_hull(df):
    """Tính toán thuật toán đường bao lồi khép kín dạng mảng numpy"""
    if df is None or len(df) < 3:
        return None
    points = df[['X', 'Y']].values
    try:
        hull = ConvexHull(points)
        boundary_points = points[hull.vertices]
        boundary_points = np.vstack([boundary_points, boundary_points[0]]) # Khép kín vòng
        return boundary_points
    except:
        return None

def process_raw_file(uploaded_file):
    """Đọc dữ liệu thô dạng bảng, tự động nhận biết dấu phân cách"""
    try:
        df = pd.read_csv(uploaded_file, sep=None, engine='python')
        return df
    except Exception as e:
        st.error(f"Lỗi khi đọc định dạng file dữ liệu: {e}")
        return None

# --- SIDEBAR: GIAO DIỆN ĐIỀU HƯỚNG TỪNG BƯỚC ---
st.sidebar.header("🗺️ LUỒNG XỬ LÝ SỐ LIỆU")
step = st.sidebar.radio("Chuyển đến bước:", [
    "[BƯỚC 1] Xác lập Bề mặt 1",
    "[BƯỚC 2] Xây dựng Boundary Tổng quát",
    "[BƯỚC 3 & 4] Chi tiết & Tính Khối lượng",
    "[BƯỚC 5] Xuất Báo cáo & File DXF"
])
# ==============================================================================
# [BƯỚC 1] XÁC LẬP BỀ MẶT TÍNH TOÁN (BỀ MẶT 1)
# ==============================================================================
if step == "[BƯỚC 1] Xác lập Bề mặt 1":
    st.subheader("📍 [BƯỚC 1] XÁC LẬP BỀ MẶT TÍNH TOÁN (BỀ MẶT 1)")
    
    file_1 = st.file_uploader("Tải lên file Mặt bằng hiện hữu (TXT/CSV)", type=["txt", "csv"], key="u_file_1")
    
    if file_1 is not None:
        df_raw = process_raw_file(file_1)
        if df_raw is not None:
            st.markdown("##### 📊 Dữ liệu thô trích xuất từ file:")
            st.dataframe(df_raw.head(5), use_container_width=True)
            
            numeric_cols = df_raw.select_dtypes(include=['number']).columns.tolist()
            auto_crs = detect_coordinate_system(df_raw, numeric_cols)
            suggestions = suggest_headings(df_raw.columns)
            
            st.markdown("##### ⚙️ Phân lập & Xác nhận dữ liệu thủ công từ kỹ sư:")
            c1, c2 = st.columns(2)
            with c1:
                crs_list = ["VN2000", "WGS84", "Tọa độ giả định"]
                selected_crs = st.selectbox("Hệ tọa độ dữ liệu:", crs_list, index=crs_list.index(auto_crs))
                st.caption(f"💡 Hệ thống tự động nhận diện gốc: **{auto_crs}**")
            
            with c2:
                gc_x, gc_y, gc_z, gc_id_col = st.columns(4)
                col_x = gc_x.selectbox("Trục X (East):", df_raw.columns, index=suggestions["E"])
                col_y = gc_y.selectbox("Trục Y (North):", df_raw.columns, index=suggestions["N"])
                col_z = gc_z.selectbox("Trục Z (Cao độ H):", df_raw.columns, index=suggestions["Z"])
                id_opts = ["-- Tự động đánh STT --"] + list(df_raw.columns)
                col_id = gc_id_col.selectbox("Cột ID (Số TT):", id_opts, index=suggestions["ID"] + 1 if suggestions["ID"] != 0 else 0)

            if st.button("🔄 CẬP NHẬT TẬP ĐIỂM BỀ MẶT 1", type="primary"):
                df_proc = pd.DataFrame()
                if col_id == "-- Tự động đánh STT --":
                    df_proc['ID'] = range(1, len(df_raw) + 1)
                else:
                    df_proc['ID'] = df_raw[col_id]
                
                df_proc['X'] = pd.to_numeric(df_raw[col_x], errors='coerce')
                df_proc['Y'] = pd.to_numeric(df_raw[col_y], errors='coerce')
                df_proc['Z'] = pd.to_numeric(df_raw[col_z], errors='coerce')
                df_proc = df_proc.dropna(subset=['X', 'Y', 'Z'])
                
                st.session_state['surface_1_df'] = df_proc
                st.session_state['surface_1_crs'] = selected_crs
                st.session_state['boundary_1'] = compute_convex_hull(df_proc)
                st.success(f"Đã chuẩn hóa thành công tập điểm Mass Points gồm {len(df_proc)} điểm thuộc Bề mặt 1!")

    if st.session_state['surface_1_df'] is not None:
        st.markdown("---")
        st.markdown("##### 📐 Mô phỏng không gian trực quan 3D (Bề mặt hiện hữu 1)")
        df_s1 = st.session_state['surface_1_df']
        bound_1 = st.session_state['boundary_1']
        
        fig = go.Figure()
        fig.add_trace(go.Scatter3d(
            x=df_s1['X'], y=df_s1['Y'], z=df_s1['Z'],
            mode='markers', marker=dict(size=3, color=df_s1['Z'], colorscale='Viridis', showscale=True),
            name='Mass Points 1'
        ))
        
        if bound_1 is not None:
            fig.add_trace(go.Scatter3d(
                x=bound_1[:, 0], y=bound_1[:, 1], z=[df_s1['Z'].min()] * len(bound_1),
                mode='lines', line=dict(color='green', width=5), name='Boundary 1 (Green)'
            ))
            
        fig.update_layout(scene=dict(aspectmode='data'), margin=dict(l=0, r=0, b=0, t=30))
        st.plotly_chart(fig, use_container_width=True)
# ==============================================================================
# [BƯỚC 2] XÂY DỰNG BOUNDARY TỔNG QUÁT
# ==============================================================================
elif step == "[BƯỚC 2] Xây dựng Boundary Tổng quát":
    st.subheader("📐 [BƯỚC 2] XÂY DỰNG BOUNDARY TỔNG QUÁT")
    
    if st.session_state['surface_1_df'] is None:
        st.warning("⚠️ Vui lòng cấu hình chuẩn hóa dữ liệu tập điểm tại [BƯỚC 1] trước khi xây dựng đường bao!")
    else:
        option_calc = st.radio("Chọn phương án tính toán phối hợp hình học:", 
                               ["1. Tính theo Cao độ thiết kế", "2. Tính so với Mặt bằng cơ sở"])
        
        if option_calc == "1. Tính theo Cao độ thiết kế":
            st.session_state['final_boundary_type'] = "Cao độ thiết kế"
            st.session_state['design_height_value'] = st.number_input("Nhập giá trị cao độ thiết kế mong muốn H (m):", value=st.session_state['design_height_value'])
            ranh_option = st.selectbox("Hình thức xác định ranh giới ranh tổng hợp:", ["Mặt bằng hiện hữu", "Ranh giới ấn định"])
            
            if ranh_option == "Mặt bằng hiện hữu":
                if st.session_state['boundary_1'] is not None:
                    poly_1 = Polygon(st.session_state['boundary_1'])
                    st.session_state['final_boundaries'] = [poly_1]
                    st.success("Đã xác lập thành công: Đường bao tổng quát sử dụng **Boundary của Bề mặt 1 (Màu Green)**.")
            
            elif ranh_option == "Ranh giới ấn định":
                file_ranh = st.file_uploader("Tải lên file dữ liệu Ranh giới ấn định thủ công (TXT/CSV)", type=["txt", "csv"], key="u_file_ranh")
                if file_ranh is not None:
                    df_ranh_raw = process_raw_file(file_ranh)
                    if df_ranh_raw is not None:
                        st.dataframe(df_ranh_raw.head(3))
                        sug_r = suggest_headings(df_ranh_raw.columns)
                        gc_r = st.columns(2)
                        rx = gc_r.selectbox("Cột trục X (Ranh):", df_ranh_raw.columns, index=sug_r["E"])
                        ry = gc_r.selectbox("Cột trục Y (Ranh):", df_ranh_raw.columns, index=sug_r["N"])
                        
                        if st.button("🏗️ XÁC ĐỊNH RANH GIỚI ẤN ĐỊNH"):
                            df_r = pd.DataFrame({'X': pd.to_numeric(df_ranh_raw[rx]), 'Y': pd.to_numeric(df_ranh_raw[ry])}).dropna()
                            b_fixed = compute_convex_hull(df_r)
                            if b_fixed is not None:
                                st.session_state['final_boundaries'] = [Polygon(b_fixed)]
                                st.success("Đã ghi nhận đường ranh giới ấn định thủ công từ kỹ sư (Màu Red)!")
        elif option_calc == "2. Tính so với Mặt bằng cơ sở":
            st.session_state['final_boundary_type'] = "Mặt bằng cơ sở"
            st.markdown("##### 🗂️ Cấu hình dữ liệu Bề mặt 2 (Mặt bằng cơ sở)")
            file_2 = st.file_uploader("Tải lên file dữ liệu trắc địa Bề mặt 2", type=["txt", "csv"], key="u_file_2")
            
            if file_2 is not None:
                df_raw_2 = process_raw_file(file_2)
                if df_raw_2 is not None:
                    sug_2 = suggest_headings(df_raw_2.columns)
                    
                    gc2_x, gc2_y, gc2_z, gc2_id_col = st.columns(4)
                    c2_x = gc2_x.selectbox("Trục X (E) Bề mặt 2:", df_raw_2.columns, index=sug_2["E"])
                    c2_y = gc2_y.selectbox("Trục Y (N) Bề mặt 2:", df_raw_2.columns, index=sug_2["N"])
                    c2_z = gc2_z.selectbox("Trục Z (H) Bề mặt 2:", df_raw_2.columns, index=sug_2["Z"])
                    c2_id = gc2_id_col.selectbox("Cột ID Bề mặt 2:", ["-- Tự động đánh STT --"] + list(df_raw_2.columns), index=sug_2["ID"]+1 if sug_2["ID"]!=0 else 0)
                    
                    if st.button("🔄 CẬP NHẬT TẬP ĐIỂM BỀ MẶT 2"):
                        df_proc_2 = pd.DataFrame()
                        df_proc_2['ID'] = range(1, len(df_raw_2) + 1) if c2_id == "-- Tự động đánh STT --" else df_raw_2[c2_id]
                        df_proc_2['X'] = pd.to_numeric(df_raw_2[c2_x])
                        df_proc_2['Y'] = pd.to_numeric(df_raw_2[c2_y])
                        df_proc_2['Z'] = pd.to_numeric(df_raw_2[c2_z])
                        df_proc_2 = df_proc_2.dropna()
                        
                        st.session_state['surface_2_df'] = df_proc_2
                        st.session_state['boundary_2'] = compute_convex_hull(df_proc_2)
                        st.success("Đã chuẩn hóa và nạp thành công bộ tập điểm dữ liệu của Bề mặt cơ sở 2!")
            
            st.markdown("##### 💠 Lựa chọn hình thức xác định ranh tổng hợp phối hợp:")
            ranh_option_2 = st.selectbox("Phương thức phối hợp không gian đường bao:", [
                "Mặt bằng hiện hữu (Sử dụng Boundary của Bề mặt 1)",
                "Ranh giới ấn định (Áp dụng đa giác ranh biên độc lập)",
                "Tổng hợp Bề mặt 1 & 2 (Hợp nhất các Boundary đa giác - Thuật toán Union)",
                "Xác định riêng Bề mặt 1, 2 (Ranh giới tổng quát gồm 2 phần độc lập)"
            ])
            
            if st.button("⚡ XÁC LẬP BOUNDARY TỔNG QUÁT TÍNH TOÁN"):
                b1 = st.session_state['boundary_1']
                b2 = st.session_state['boundary_2']
                
                if "Mặt bằng hiện hữu" in ranh_option_2 and b1 is not None:
                    st.session_state['final_boundaries'] = [Polygon(b1)]
                    st.success("Xác lập thành công ranh tổng quát sử dụng đường bao Bề mặt hiện hữu 1 (Màu Green).")
                elif "Tổng hợp Bề mặt 1 & 2" in ranh_option_2 and b1 is not None and b2 is not None:
                    p1 = Polygon(b1)
                    p2 = Polygon(b2)
                    union_poly = unary_union([p1, p2])
                    st.session_state['final_boundaries'] = [union_poly] if union_poly.geom_type == 'Polygon' else list(union_poly.geoms)
                    st.success("Thuật toán tích hợp không gian (Union) đã gộp ranh giới hai mặt thành công (Màu White)!")
                elif "Xác định riêng" in ranh_option_2 and b1 is not None and b2 is not None:
                    st.session_state['final_boundaries'] = [Polygon(b1), Polygon(b2)]
                    st.success("Đã ghi nhận cấu trúc ranh giới tổng quát độc lập phân rã gồm 2 phần tự động!")
# ==============================================================================
# [BƯỚC 3 & 4] TÍNH TOÁN KHỐI LƯỢNG NÂNG CAO (TIN MẠNG TAM GIÁC & PRISM METHOD)
# ==============================================================================
elif step == "[BƯỚC 3 & 4] Chi tiết & Tính Khối lượng":
    st.subheader("📊 [BƯỚC 3 & 4] TÍNH TOÁN KHỐI LƯỢNG (MÔ HÌNH TIN & PRISM METHOD)")
    
    if st.session_state['surface_1_df'] is None or not st.session_state['final_boundaries']:
        st.warning("⚠️ Vui lòng cấu hình đầy đủ dữ liệu Bề mặt 1 và xác lập ranh giới tổng quát ở các bước trước!")
    else:
        from scipy.spatial import Delaunay
        from shapely.geometry import Point as ShapePoint
        
        df1 = st.session_state['surface_1_df']
        pts1 = df1[['X', 'Y']].values
        z1 = df1['Z'].values
        vung_ranh = unary_union(st.session_state['final_boundaries'])
        
        tri1 = Delaunay(pts1)
        total_cut, total_fill, valid_triangles_count = 0.0, 0.0, 0
        
        if st.session_state['final_boundary_type'] == "Cao độ thiết kế":
            h_tk = st.session_state['design_height_value']
            for simplex in tri1.simplices:
                p_tri = pts1[simplex]
                centroid = ShapePoint(p_tri[:, 0].mean(), p_tri[:, 1].mean())
                if vung_ranh.contains(centroid):
                    valid_triangles_count += 1
                    x, y = p_tri[:, 0], p_tri[:, 1]
                    area_2d = 0.5 * np.abs(x[0]*(y[1]-y[2]) + x[1]*(y[2]-y[0]) + x[2]*(y[0]-y[1]))
                    h_avg = (z1[simplex] - h_tk).mean()
                    v_prism = area_2d * h_avg
                    if v_prism > 0: total_cut += v_prism
                    else: total_fill += abs(v_prism)
                        
        elif st.session_state['final_boundary_type'] == "Mặt bằng cơ sở" and st.session_state['surface_2_df'] is not None:
            df2 = st.session_state['surface_2_df']
            pts2 = df2[['X', 'Y']].values
            z2 = df2['Z'].values
            tri2 = Delaunay(pts2)
            
            def interpolate_tin_z(point, delaunay_obj, z_values):
                idx = delaunay_obj.find_simplex(point)
                if idx < 0: return None
                b = delaunay_obj.transform[idx]
                r = b[:2].dot(point - delaunay_obj.points[delaunay_obj.simplices[idx, 2]])
                c = np.array([r, r, 1 - r - r])
                return np.dot(c, z_values[delaunay_obj.simplices[idx]])

            for simplex in tri1.simplices:
                p_tri = pts1[simplex]
                centroid = ShapePoint(p_tri[:, 0].mean(), p_tri[:, 1].mean())
                if vung_ranh.contains(centroid):
                    valid_triangles_count += 1
                    x, y = p_tri[:, 0], p_tri[:, 1]
                    area_2d = 0.5 * np.abs(x[0]*(y[1]-y[2]) + x[1]*(y[2]-y[0]) + x[2]*(y[0]-y[1]))
                    z_s1 = z1[simplex]
                    z_s2 = []
                    for i, pt in enumerate(p_tri):
                        z_val = interpolate_tin_z(pt, tri2, z2)
                        z_s2.append(z_val if z_val is not None else z_s1[i])
                    h_diff_avg = (z_s1 - np.array(z_s2)).mean()
                    v_prism = area_2d * h_diff_avg
                    if v_prism > 0: total_cut += v_prism
                    else: total_fill += abs(v_prism)

        st.success(f"Đã xây dựng mô hình mạng tam giác TIN và chạy Prism Method lăng trụ đứng thành công ({valid_triangles_count} lăng trụ tam giác hợp lệ).")
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Khối lượng Đào thực tế (V_cut)", f"{total_cut:,.2f} m³")
        mc2.metric("Khối lượng Đắp thực tế (V_fill)", f"{total_fill:,.2f} m³")
        mc3.metric("Khối lượng chênh lệch (Net)", f"{(total_cut - total_fill):,.2f} m³", delta=f"{(total_cut - total_fill):,.2f}")

# ==============================================================================
# [BƯỚC 5] XUẤT BÁO CÁO & XUẤT FILE BẢN VẼ ĐỒ HỌA DXF
# ==============================================================================
elif step == "[BƯỚC 5] Xuất Báo cáo & File DXF":
    st.subheader("💾 [BƯỚC 5] KẾT XUẤT BÁO CÁO VÀ FILE BẢN VẼ DXF CHUẨN KỸ THUẬT")
    if st.session_state['surface_1_df'] is None:
        st.warning("⚠️ Thiếu cấu trúc dữ liệu nền trắc địa để xuất bản vẽ CAD. Vui lòng thực hiện tải file ở Bước 1.")
    else:
        st.write("Hệ thống biên dịch các thực thể Vector để cấu thành cấu trúc file AutoCAD `.dxf` phân tầng Layer màu sắc chuyên dụng:")
        st.markdown("* 🟢 **Layer_Be_Mat_1** (Màu Green - Mã ACI 3) | * 🔵 **Layer_Be_Mat_2** (Màu Blue - Mã ACI 5) | * ⚪ **Layer_Ranh_Tong_Hop** (Màu White - Mã ACI 7)")
        
        if st.button("🛠️ KHỔI TẠO VÀ XUẤT FILE DXF BẢN VẼ", type="primary"):
            doc = ezdxf.new('R2010')
            msp = doc.modelspace()
            doc.layers.new(name='Layer_Be_Mat_1', dxfattribs={'color': 3}) 
            doc.layers.new(name='Layer_Be_Mat_2', dxfattribs={'color': 5}) 
            doc.layers.new(name='Layer_Ranh_Tong_Hop', dxfattribs={'color': 7}) 
            
            df1 = st.session_state['surface_1_df']
            for _, row in df1.iterrows():
                msp.add_point((row['X'], row['Y'], row['Z']), dxfattribs={'layer': 'Layer_Be_Mat_1'})
                msp.add_text(f"{row['Z']:.2f}", dxfattribs={'layer': 'Layer_Be_Mat_1', 'height': 0.4}).set_placement((row['X'] + 0.15, row['Y'] + 0.15, row['Z']))
            
            if st.session_state['boundary_1'] is not None:
                pts_b1 = [(float(pt[0]), float(pt[1])) for pt in st.session_state['boundary_1']]
                msp.add_lwpolyline(pts_b1, dxfattribs={'layer': 'Layer_Be_Mat_1', 'flags': 1})
            if st.session_state['boundary_2'] is not None:
                pts_b2 = [(float(pt[0]), float(pt[1])) for pt in st.session_state['boundary_2']]
                msp.add_lwpolyline(pts_b2, dxfattribs={'layer': 'Layer_Be_Mat_2', 'flags': 1})
            if st.session_state['final_boundaries']:
                for poly in st.session_state['final_boundaries']:
                    pts_fb = [(float(pt[0]), float(pt[1])) for pt in poly.exterior.coords]
                    msp.add_lwpolyline(pts_fb, dxfattribs={'layer': 'Layer_Ranh_Tong_Hop', 'flags': 1})

            out_stream = io.StringIO()
            doc.write(out_stream)
            dxf_bytes = out_stream.getvalue().encode('utf-8')
            st.download_button(label="📥 TẢI XUỐNG FILE XUẤT DXF BẢN VẼ", data=dxf_bytes, file_name="Bao_Cao_Ban_Ve_Trac_Dia.dxf", mime="application/dxf")
            st.success("Hệ thống Vector CAD đã biên dịch thành công!")
