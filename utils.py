import pandas as pd
import numpy as np
import ezdxf
import io

def parse_points(file, x_col, y_col, z_col, id_col):
    """Chuẩn hóa cấu trúc bảng tọa độ đầu vào sang chuẩn đồ họa CAD (X, Y, Z, ID)"""
    try:
        df = pd.read_csv(file, sep=None, engine='python')
        rename_dict = {x_col: 'X', y_col: 'Y', z_col: 'Z'}
        if id_col and id_col != "Tự động tạo ID":
            rename_dict[id_col] = 'ID'
        df = df.rename(columns=rename_dict)
        
        if 'ID' not in df.columns or id_col == "Tự động tạo ID":
            df['ID'] = range(1, len(df) + 1)
            
        return df[['ID', 'X', 'Y', 'Z']].dropna()
    except Exception as e:
        return None

def interpolate_tin_z(tri, pts_3d, query_pts):
    """Nội suy cao độ hình học dựa trên lưới đan tam giác chuẩn Civil3D"""
    simplex = tri.find_simplex(query_pts)
    valid = simplex >= 0
    z_res = np.full(query_pts.shape, np.nan)
    
    for i in np.where(valid):
        s = simplex[i]
        v = tri.simplices[s]
        b = tri.transform[s, :2].dot((query_pts[i] - tri.transform[s, 2]).T)
        bary = np.r_[b, 1 - b.sum()]
        z_res[i] = np.dot(bary, pts_3d[v, 2])
    return z_res
    def extract_boundary_edges(tri):
    """Trích xuất các đoạn thẳng biên bên ngoài của lưới tam giác Delaunay"""
    edges = {}
    for simplex in tri.simplices:
        for i in range(3):
            u, v = simplex[i], simplex[(i + 1) % 3]
            edge = tuple(sorted((u, v)))
            edges[edge] = edges.get(edge, 0) + 1
    # Đường biên ngoài cùng là những cạnh chỉ thuộc về đúng 1 tam giác
    boundary_edges = [edge for edge, count in edges.items() if count == 1]
    return boundary_edges

def export_to_dxf(p1, p2, tri1, tri2, min_x, max_x, min_y, max_y, h_size, id_size):
    """Khởi tạo cấu trúc dữ liệu bản vẽ DXF phân tách lớp độc lập phục vụ AutoCAD (Sửa lỗi Layer Color)"""
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    
    # Cấu hình màu sắc mã màu CAD chuẩn (ACI) cho từng Layer kỹ thuật độc lập
    layers_config = {
        "TIN_SURFACE_1": 3,     # Green (Xanh lá)
        "TIN_SURFACE_2": 4,     # Cyan (Xanh lam)
        "BBORDER": 1,           # Red (Đỏ)
        "POINTS_SURFACE_1": 7,  # White (Trắng)
        "POINTS_SURFACE_2": 2   # Yellow (Vàng)
    }
    
    # Khởi tạo Layer an toàn thông qua việc gán thuộc tính đối tượng trực tiếp
    for name, color_code in layers_config.items():
        if name not in doc.layers:
            layer = doc.layers.new(name=name)
            layer.color = color_code
        
    # 1. Xuất lưới tam giác TIN bề mặt 1 (Dạng khối hình học 3DFACE)
    for tri in tri1.simplices:
        pts = p1.iloc[tri][['X', 'Y', 'Z']].values
        msp.add_3dface(pts, dxfattribs={'layer': 'TIN_SURFACE_1'})
        
    # 2. Xuất lưới tam giác TIN bề mặt 2 (Dạng khối hình học 3DFACE)
    for tri in tri2.simplices:
        pts = p2.iloc[tri][['X', 'Y', 'Z']].values
        msp.add_3dface(pts, dxfattribs={'layer': 'TIN_SURFACE_2'})
        
    # 3. Xuất đường bao ranh giới giới hạn trực giao BBorder dạng khép kín an toàn
    bbox_vertices = [(min_x, min_y), (max_x, min_y), (max_x, max_y), (min_x, max_y)]
    polyline = msp.add_lwpolyline(bbox_vertices, dxfattribs={'layer': 'BBORDER'})
    polyline.closed = True  # Đóng kín đường bao
        
    # 4. Xuất các điểm thuộc tính Bề mặt 1: Gồm POINT, cao độ H và số TT (ID nhỏ bằng 1/2 cao độ)
    for _, row in p1.iterrows():
        msp.add_point((row['X'], row['Y'], row['Z']), dxfattribs={'layer': 'POINTS_SURFACE_1'})
        # Text Cao độ H
        text_h = msp.add_text(f"{row['Z']:.2f}", dxfattribs={'layer': 'POINTS_SURFACE_1', 'height': h_size})
        text_h.set_placement((row['X'] + 0.1, row['Y'] + 0.1, row['Z']))
        # Text Số thứ tự (Tỷ lệ 1/2 tự động)
        text_id = msp.add_text(f"#{int(row['ID'])}", dxfattribs={'layer': 'POINTS_SURFACE_1', 'height': id_size})
        text_id.set_placement((row['X'] + 0.1, row['Y'] - (h_size * 0.8), row['Z']))
        
    # 5. Xuất các điểm thuộc tính Bề mặt 2: Chỉ bao gồm POINT và Số thứ tự (ID)
    for _, row in p2.iterrows():
        msp.add_point((row['X'], row['Y'], row['Z']), dxfattribs={'layer': 'POINTS_SURFACE_2'})
        text_bm2_id = msp.add_text(f"#{int(row['ID'])}", dxfattribs={'layer': 'POINTS_SURFACE_2', 'height': id_size})
        text_bm2_id.set_placement((row['X'] + 0.1, row['Y'] + 0.1, row['Z']))
        
    out_stream = io.StringIO()
    doc.write(out_stream)
    return out_stream.getvalue()
    
