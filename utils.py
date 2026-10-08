import pandas as pd
import numpy as np
from scipy.spatial import ConvexHull

# Thử kiểm tra xem thư viện đọc CAD có sẵn hay không
try:
    import ezdxf
    EZDXF_AVAILABLE = True
except ImportError:
    EZDXF_AVAILABLE = False

def parse_txt_to_df(uploaded_file):
    """Đọc file TXT hoặc CSV thành DataFrame"""
    content = uploaded_file.getvalue().decode("utf-8")
    lines = content.strip().split('\n')
    
    # Tự động đoán dấu phân cách (Dấu phẩy, Tab, hoặc khoảng trắng)
    sample = lines[0]
    sep = ',' if ',' in sample else ('\t' if '\t' in sample else r'\s+')
    
    uploaded_file.seek(0)
    df = pd.read_csv(uploaded_file, sep=sep, header=None if not sample.replace('.', '', 1).isdigit() else 'infer')
    return df

def parse_dxf_to_df(uploaded_file):
    """Trích xuất tọa độ XYZ từ file CAD (DXF)"""
    if not EZDXF_AVAILABLE:
        return None
    try:
        dxf_bytes = uploaded_file.getvalue().decode("utf-8", errors="ignore")
        doc = ezdxf.readstring(dxf_bytes)
        msp = doc.modelspace()
        
        points = []
        # Lấy các đối tượng POINT trong bản vẽ
        for p in msp.query('POINT'):
            points.append(p.dxf.location)
        # Lấy các đỉnh từ đường LWPOLYLINE
        for pl in msp.query('LWPOLYLINE'):
            for p in pl.get_points():
                z = p[2] if len(p) > 2 else 0.0
                points.append((p[0], p[1], z))
                
        if len(points) == 0:
            return None
        return pd.DataFrame(points, columns=['X', 'Y', 'Z'])
    except Exception:
        return None

def detect_crs(df, x_col, y_col):
    """Tự động nhận dạng hệ tọa độ (VN2000 hoặc WGS84) dựa trên dải số liệu"""
    try:
        x_min, x_max = df[x_col].min(), df[x_col].max()
        y_min, y_max = df[y_col].min(), df[y_col].max()
        
        # Đặc trưng hệ VN2000: X có 6 chữ số, Y có 7 chữ số tại Việt Nam
        if (100000 <= x_min <= 999999) and (1000000 <= y_min <= 3000000):
            return "VN2000 (Hệ tọa độ quốc gia Việt Nam)"
        # Đặc trưng WGS84: Kinh độ -180 đến 180, Vĩ độ -90 đến 90
        elif (-180 <= x_min <= 180) and (-90 <= y_min <= 90):
            return "WGS84 (Kinh vĩ độ quốc tế)"
        else:
            return "Tọa độ giả định (Hệ tọa độ nội bộ / Local)"
    except Exception:
        return "Không thể tự động nhận diện"

def compute_convex_hull(points_2d):
    """Tìm ranh giới bao ngoài lồi (Convex Hull) từ tập điểm 2D"""
    if len(points_2d) < 3:
        return points_2d
    hull = ConvexHull(points_2d)
    hull_points = points_2d[hull.vertices]
    # Nối điểm cuối trùng điểm đầu để tạo đa giác kín khi vẽ đường ranh
    hull_points = np.vstack([hull_points, hull_points[0]])
    return hull_points
