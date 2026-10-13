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
    z_res = np.full(query_pts.shape[0], np.nan)
    
    for i in np.where(valid)[0]:
        s = simplex[i]
        v = tri.simplices[s]
        b = tri.transform[s, :2].dot((query_pts[i] - tri.transform[s, 2]).T)
        bary = np.r_[b, 1 - b.sum()]
        z_res[i] = np.dot(bary, pts_3d[v, 2])
    return z_res

def export_to_dxf(p1, p2, tri1, tri2, min_x, max_x, min_y, max_y, h_size, id_size):
    """Khởi tạo cấu trúc dữ liệu bản vẽ DXF phân tách lớp độc lập phục vụ AutoCAD"""
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    
    layers_config = {
        "TIN_SURFACE_1": 3,     # Green
        "TIN_SURFACE_2": 4,     # Cyan
        "BBORDER": 1,           # Red
        "POINTS_SURFACE_1": 7,  # White
        "POINTS_SURFACE_2": 2   # Yellow
    }
    for name, color in layers_config.items():
        doc.layers.new(name=name, dxfattribs={'color': color})
        
    for tri in tri1.simplices:
        pts = p1.iloc[tri][['X', 'Y', 'Z']].values
        msp.add_3dface(pts, dxfattribs={'layer': 'TIN_SURFACE_1'})
        
    for tri in tri2.simplices:
        pts = p2.iloc[tri][['X', 'Y', 'Z']].values
        msp.add_3dface(pts, dxfattribs={'layer': 'TIN_SURFACE_2'})
        
    bbox_vertices = [(min_x, min_y), (max_x, min_y), (max_x, max_y), (min_x, max_y)]
    msp.add_lwpolyline(bbox_vertices, dxfattribs={'layer': 'BBORDER', 'is_closed': True})
        
    for _, row in p1.iterrows():
        msp.add_point((row['X'], row['Y'], row['Z']), dxfattribs={'layer': 'POINTS_SURFACE_1'})
        msp.add_text(f"{row['Z']:.2f}", dxfattribs={'layer': 'POINTS_SURFACE_1', 'height': h_size}).set_placement((row['X'] + 0.1, row['Y'] + 0.1, row['Z']))
        msp.add_text(f"#{int(row['ID'])}", dxfattribs={'layer': 'POINTS_SURFACE_1', 'height': id_size}).set_placement((row['X'] + 0.1, row['Y'] - (h_size * 0.8), row['Z']))
        
    for _, row in p2.iterrows():
        msp.add_point((row['X'], row['Y'], row['Z']), dxfattribs={'layer': 'POINTS_SURFACE_2'})
        msp.add_text(f"#{int(row['ID'])}", dxfattribs={'layer': 'POINTS_SURFACE_2', 'height': id_size}).set_placement((row['X'] + 0.1, row['Y'] + 0.1, row['Z']))
        
    out_stream = io.StringIO()
    doc.write(out_stream)
    return out_stream.getvalue()
