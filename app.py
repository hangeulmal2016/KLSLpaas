import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import io

# CHỈ IMPORT ĐÚNG 4 HÀM CÓ TRONG FILE UTILS.PY MỚI (Đã loại bỏ hoàn toàn export_dxf_bytes)
from utils import parse_txt_to_df, parse_dxf_to_df, detect_crs_and_headings, compute_convex_hull

st.set_page_config(page_title="Web App Trắc Địa", page_icon="📐", layout="wide")
st.title("📐 Web App Xử lý Số liệu Trắc địa")
st.caption("Phương án 1 | Tối ưu hóa tương tác đa khung Focus & Overview")

if 'bm1_df' not in st.session_state: st.session_state.bm1_df = None
if 'bm2_df' not in st.session_state: st.session_state.bm2_df = None
if 'ranh_an_dinh_df' not in st.session_state: st.session_state.ranh_an_dinh_df = None

def local_export_dxf(layers_dict):
    """Hàm xuất DXF nội bộ chịu trách nhiệm vẽ Point ID, Cao độ và Boundary mã màu"""
    try:
        import ezdxf
        doc = ezdxf.new('R2000')
        msp = doc.modelspace()
        for layer_name, data in layers_dict.items():
            color = data.get('color_idx', 7)
            doc.layers.new(name=layer_name, dxfattribs={'color': color})
            df_pts = data.get('points')
            if df_pts is not None and not df_pts.empty:
                for _, row in df_pts.iterrows():
                    x, y, z, p_id = row['X'], row['Y'], row['Z'], str(row['ID'])
                    msp.add_point((x, y, z), dxfattribs={'layer': layer_name})
                    msp.add_text(f"H:{z:.2f}", dxfattribs={'layer': layer_name, 'height': 0.4}).set_pos((x + 0.3, y + 0.3, z))
                    msp.add_text(f"ID:{p_id}", dxfattribs={'layer': layer_name, 'height': 0.4}).set_pos((x + 0.3, y - 0.3, z))
            poly = data.get('boundary')
            if poly is not None and len(poly) > 0:
                msp.add_polyline3d(poly, dxfattribs={'layer': layer_name})
        out_buf = io.StringIO()
        doc.write(out_buf)
        return out_buf.getvalue().encode('utf-8')
    except Exception: return b""

def process_surface_upload(uploaded_file, key_prefix):
    df_raw = parse_txt_to_df(uploaded_file) if uploaded_file.name.split('.')[-1].lower() in ['txt', 'csv'] else parse_dxf_to_df(uploaded_file)
    if df_raw is not None:
        crs_name, headings = detect_crs_and_headings(df_raw)
        st.info(f"🤖 Hệ tọa độ nhận dạng: {crs_name}")
        cols = list(df_raw.columns)
        c1, c2, c3, c4 = st.columns(4)
        with c1: x_col = st.selectbox("Cột X:", cols, index=0, key=f"{key_prefix}_x")
        with c2: y_col = st.selectbox("Cột Y:", cols, index=1 if len(cols)>1 else 0, key=f"{key_prefix}_y")
        with c3: z_col = st.selectbox("Cột Z:", cols, index=2 if len(cols)>2 else 0, key=f"{key_prefix}_z")
        with c4: id_col = st.selectbox("Cột ID:", ["-- Tự động thêm --"] + cols, key=f"{key_prefix}_id")
        
        df_proc = pd.DataFrame()
        df_proc['X'] = df_raw[x_col].astype(float)
        df_proc['Y'] = df_raw[y_col].astype(float)
        df_proc['Z'] = df_raw[z_col].astype(float)
        df_proc['ID'] = range(1, len(df_proc) + 1) if id_col == "-- Tự động thêm --" else df_raw[id_col]
        return df_proc[['ID', 'X', 'Y', 'Z']]
    return None

st.sidebar.header("📌 QUY TRÌNH THỰC HIỆN")
step = st.sidebar.radio("Chọn bước ứng dụng:", ["🔥 [BƯỚC 1] Xác lập bề mặt tính toán 1", "🗺️ [BƯỚC 2] Xây dựng Boundary tổng quát", "🧱 [BƯỚC 3-5] Các bước xử lý tiếp theo"])
if "BƯỚC 1" in step:
    st.header("⚙️ [BƯỚC 1] Xác lập Bề mặt tính toán (Bề mặt 1)")
    file_b1 = st.file_uploader("Tải file Mặt bằng hiện hữu (DXF/TXT/CSV):", type=["txt", "csv", "dxf"], key="upload_b1")
    if file_b1 is not None:
        df_normalized = process_surface_upload(file_b1, "b1")
        if df_normalized is not None:
            st.write("📊 Dữ liệu mẫu Bề mặt 1 đã chuẩn hóa:")
            st.dataframe(df_normalized.head(10), use_container_width=True)
            if st.button("💾 Cập nhật tập điểm Bề mặt 1"):
                st.session_state.bm1_df = df_normalized
                st.success("Đã lưu tập điểm Bề mặt 1 thành công!")
                
            if st.session_state.bm1_df is not None:
                h_b1 = compute_convex_hull(st.session_state.bm1_df[['X', 'Y']].values)
                hull_b1_3d = np.hstack([h_b1, np.full((len(h_b1), 1), st.session_state.bm1_df['Z'].min())])
                dxf_b1 = local_export_dxf({"BEMAT_1": {"points": st.session_state.bm1_df, "boundary": hull_b1_3d, "color_idx": 3}})
                st.download_button("📥 Xuất file DXF Bề mặt 1 (Boundary Green)", data=dxf_b1, file_name="Bemat1_Boundary_Green.dxf", mime="application/dxf")

elif "BƯỚC 2" in step:
    st.header("🗺️ [BƯỚC 2] Xây dựng Boundary tổng quát")
    if st.session_state.bm1_df is None:
        st.warning("⚠️ Vui lòng hoàn thành [BƯỚC 1] trước.")
    else:
        pa_tinh = st.radio("Chọn Phương án tính toán:", ["1. Tính theo Cao độ thiết kế", "2. Tính so với Mặt bằng cơ sở"])
        boundary_mode, z_design = "Mặt bằng hiện hữu", 0.0
        
        if "1." in pa_tinh:
            z_design = st.number_input("Nhập giá trị cao độ thiết kế (m):", value=0.0)
            boundary_mode = st.selectbox("Lựa chọn hình thức ranh:", ["Mặt bằng hiện hữu", "Ranh giới ấn định"], key="bm_mode_1")
            if boundary_mode == "Ranh giới ấn định":
                file_ranh = st.file_uploader("Tải file Ranh giới ấn định ngoài:", type=["txt", "csv", "dxf"], key="ranh_ad_1")
                if file_ranh is not None: st.session_state.ranh_an_dinh_df = process_surface_upload(file_ranh, "rad1")
        else:
            st.subheader("📍 Xác lập Bề mặt cơ sở (Bề mặt 2)")
            file_b2 = st.file_uploader("Tải file Mặt bằng cơ sở 2:", type=["txt", "csv", "dxf"], key="upload_b2")
            if file_b2 is not None:
                df_b2_normalized = process_surface_upload(file_b2, "b2")
                if df_b2_normalized is not None:
                    st.write("📊 Dữ liệu mẫu Bề mặt 2:")
                    st.dataframe(df_b2_normalized.head(10), use_container_width=True)
                    st.session_state.bm2_df = df_b2_normalized
                    st.success("Đã nạp số liệu Bề mặt 2 thành công.")
            boundary_mode = st.selectbox("Lựa chọn hình thức ranh:", ["Mặt bằng hiện hữu", "Ranh giới ấn định", "Tổng hợp Bề mặt 1&2", "Xác định riêng Bề mặt 1,2"], key="bm_mode_2")
            if boundary_mode == "Ranh giới ấn định":
                file_ranh = st.file_uploader("Tải file Ranh giới ấn định ngoài:", type=["txt", "csv", "dxf"], key="ranh_ad_2")
                if file_ranh is not None: st.session_state.ranh_an_dinh_df = process_surface_upload(file_ranh, "rad2")
        st.subheader("📊 Khung Tổng Quan Các Boundary (Overview)")
        bm1_pts = st.session_state.bm1_df[['X', 'Y']].values
        hull_b1 = compute_convex_hull(bm1_pts)
        len_b1 = len(hull_b1) - 1
        len_rad = len(compute_convex_hull(st.session_state.ranh_an_dinh_df[['X', 'Y']].values)) - 1 if st.session_state.ranh_an_dinh_df is not None else 0
        len_b2 = len(compute_convex_hull(st.session_state.bm2_df[['X', 'Y']].values)) - 1 if st.session_state.bm2_df is not None else 0
        len_white = len(compute_convex_hull(np.vstack([bm1_pts, st.session_state.bm2_df[['X', 'Y']].values]))) - 1 if st.session_state.bm2_df is not None else 0

        ov_c1, ov_c2, ov_c3, ov_c4 = st.columns(4)
        with ov_c1: st.metric(label="🔴 Ranh ấn định", value=f"{len_rad} Đỉnh", delta="Red Layer")
        with ov_c2: st.metric(label="🟢 Ranh Bề mặt 1", value=f"{len_b1} Đỉnh", delta="Green Layer")
        with ov_c3: st.metric(label="🔵 Ranh Bề mặt 2", value=f"{len_b2} Đỉnh", delta="Blue Layer")
        with ov_c4: st.metric(label="⚪ Ranh Tổng hợp", value=f"{len_white} Đỉnh", delta="White Layer")

        st.markdown("---")
        st.subheader("🏁 [KẾT THÚC] Chế độ hiển thị Boundary")
        st.markdown("#### 🎯 Khung 2: Focus (Chọn đỉnh ranh trên đồ thị để định vị không gian)")
        fig_fc = go.Figure()
        if boundary_mode == "Mặt bằng hiện hữu":
            fig_fc.add_trace(go.Scatter(x=hull_b1[:, 0], y=hull_b1[:, 1], mode='lines+markers', line=dict(color='green', width=4)))
        elif boundary_mode == "Ranh giới ấn định" and st.session_state.ranh_an_dinh_df is not None:
            rad_pts = st.session_state.ranh_an_dinh_df[['X', 'Y']].values
            fig_fc.add_trace(go.Scatter(x=compute_convex_hull(rad_pts)[:, 0], y=compute_convex_hull(rad_pts)[:, 1], mode='lines+markers', line=dict(color='red', width=4)))
        elif boundary_mode == "Tổng hợp Bề mặt 1&2" and st.session_state.bm2_df is not None:
            hull_white = compute_convex_hull(np.vstack([bm1_pts, st.session_state.bm2_df[['X', 'Y']].values]))
            fig_fc.add_trace(go.Scatter(x=hull_white[:, 0], y=hull_white[:, 1], mode='lines+markers', line=dict(color='white', width=4)))
        elif boundary_mode == "Xác định riêng Bề mặt 1,2" and st.session_state.bm2_df is not None:
            fig_fc.add_trace(go.Scatter(x=hull_b1[:, 0], y=hull_b1[:, 1], mode='lines+markers', line=dict(color='green', width=3)))
            fig_fc.add_trace(go.Scatter(x=compute_convex_hull(st.session_state.bm2_df[['X', 'Y']].values)[:, 0], y=compute_convex_hull(st.session_state.bm2_df[['X', 'Y']].values)[:, 1], mode='lines+markers', line=dict(color='blue', width=3)))
            
        fig_fc.update_layout(margin=dict(l=10, r=10, b=10, t=10), height=350, xaxis=dict(showgrid=True), yaxis=dict(showgrid=True, scaleanchor="x", scaleratio=1), clickmode='event')
        selected_point = st.plotly_chart(fig_fc, use_container_width=True, config={'responsive': True}, key="chart_focus", on_select="rerun")
        
        highlight_x, highlight_y = None, None
        if selected_point and "selection" in selected_point and "points" in selected_point["selection"] and len(selected_point["selection"]["points"]) > 0:
            pts_data = selected_point["selection"]["points"]
            highlight_x = pts_data.get("x")
            highlight_y = pts_data.get("y")
            if highlight_x is not None: st.toast(f"🎯 Định vị đỉnh ranh: X={highlight_x:.2f}, Y={highlight_y:.2f}", icon="📍")

        st.markdown("#### 🌐 Khung 1: Overview (Địa hình 3D)")
        fig_ov = go.Figure()
        z_m1 = st.session_state.bm1_df['Z'].min()
        fig_ov.add_trace(go.Scatter3d(x=st.session_state.bm1_df['X'], y=st.session_state.bm1_df['Y'], z=st.session_state.bm1_df['Z'], mode='markers', marker=dict(size=2, color='cyan', opacity=0.8)))
        if "2." in pa_tinh and st.session_state.bm2_df is not None:
            fig_ov.add_trace(go.Scatter3d(x=st.session_state.bm2_df['X'], y=st.session_state.bm2_df['Y'], z=st.session_state.bm2_df['Z'], mode='markers', marker=dict(size=2, color='magenta', opacity=0.8)))
        if highlight_x is not None and highlight_y is not None:
            fig_ov.add_trace(go.Scatter3d(x=[highlight_x], y=[highlight_y], z=[st.session_state.bm1_df['Z'].mean()], mode='markers', marker=dict(size=8, color='yellow', symbol='diamond')))
            
        fig_ov.update_layout(margin=dict(l=0, r=0, b=0, t=10), height=350, showlegend=False)
        st.plotly_chart(fig_ov, use_container_width=True, config={'responsive': True}, key="chart_overview")
        
        st.markdown("### 💾 [BƯỚC 5] Xuất báo cáo bản vẽ kỹ thuật")
        layers_config = {}
        layers_config["BEMAT_1"] = {"points": st.session_state.bm1_df, "boundary": np.hstack([hull_b1, np.full((len(hull_b1), 1), z_m1)]), "color_idx": 3}
        if st.session_state.bm2_df is not None:
            h_b2 = compute_convex_hull(st.session_state.bm2_df[['X', 'Y']].values)
            layers_config["BEMAT_2"] = {"points": st.session_state.bm2_df, "boundary": np.hstack([h_b2, np.full((len(h_b2), 1), st.session_state.bm2_df['Z'].min())]), "color_idx": 5}
        if st.session_state.ranh_an_dinh_df is not None:
            h_rad = compute_convex_hull(st.session_state.ranh_an_dinh_df[['X', 'Y']].values)
            layers_config["RANH_AN_DINH"] = {"points": st.session_state.ranh_an_dinh_df, "boundary": np.hstack([h_rad, np.full((len(h_rad), 1), z_m1)]), "color_idx": 1}
        if st.session_state.bm2_df is not None and boundary_mode == "Tổng hợp Bề mặt 1&2":
            h_wh = compute_convex_hull(np.vstack([bm1_pts, st.session_state.bm2_df[['X', 'Y']].values]))
            layers_config["RANH_TONG_HOP"] = {"points": None, "boundary": np.hstack([h_wh, np.full((len(h_wh), 1), min(z_m1, st.session_state.bm2_df['Z'].min()))]), "color_idx": 7}
            
        dxf_final = local_export_dxf(layers_config)
        st.download_button("📥 Tải bản vẽ tổng hợp DXF (Full Layers & Colors)", data=dxf_final, file_name="BaoCao_TracDia_TongHop.dxf", mime="application/dxf")
else:
    st.header("🧱 Phân rã cấu trúc các module tiếp theo (Bước 3 - 4)")
    st.write("Khu vực phát triển tiếp thuật toán lưới ô vuông trắc địa tính toán khối lượng đào đắp.")
