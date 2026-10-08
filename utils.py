import pandas as pd
import numpy as np
from scipy.spatial import ConvexHull

try:
    import ezdxf
    EZDXF_AVAILABLE = True
except ImportError:
    EZDXF_AVAILABLE = False

def parse_txt_to_df(uploaded_file):
    """Đọc file TXT hoặc CSV thành DataFrame"""
    content = uploaded_file.getvalue().decode("utf-8")
    lines = content.strip().split('\n')
    sep = ',' if ',' in lines[0] else ('\t' if '\t' in lines[0] else r'\s+')
    uploaded_file.seek(0)
    df = pd.read_csv(uploaded_file, sep=sep, header=None if not lines[0].replace('.', '', 1).replace('-', '', 1).isdigit() else 'infer')
    return df

def parse_dxf_to_df(uploaded_file):
    """Trích xuất dữ liệu XYZ từ file DXF"""
    if not EZDXF_AVAILABLE:
        return None
    try:
        dxf_bytes = uploaded_file.getvalue().decode("utf-8", errors="ignore")
        doc = ezdxf.readstring(dxf_bytes)
        msp = doc.modelspace()
        points = []
        for p in msp.query('POINT'):
            points.append(p.dxf.location)
        for pl in msp.query('LWPOLYLINE'):
            for p in pl.get_points():
                z = p[2] if len(p) > 2 else 0.0
                points.append((p[0], p[1], z))
        if len(points) == 0:
            return None
        return pd.DataFrame(points, columns=[0, 1, 2])
    except Exception:
        return None

def detect_crs_and_headings(df):
    """Tự động nhận dạng hệ tọa độ và thiết lập tên heading gợi ý"""
    try:
        # Giả định lấy cột đầu và cột hai kiểm tra dải số liệu cơ bản
        c0_min, c0_max = df.iloc[:, 0].min(), df.iloc[:, 0].max()
        c1_min, c1_max = df.iloc[:, 1].min(), df.iloc[:, 1].max()
        
        # Kiểm tra VN2000 tiêu chuẩn (X ~ 6 chữ số, Y ~ 7 chữ số) hoặc ngược lại tùy thói quen trắc địa
        if ((100000 <= c0_min <= 999999) or (1000000 <= c0_min <= 3000000)) and \
           ((100000 <= c1_min <= 999999) or (1000000 <= c1_min <= 3000000)):
            return "VN2000", {"X": "North (X)", "Y": "East (Y)", "Z": "H (Cao độ)", "ID": "ID Điểm"}
        
        # Kiểm tra WGS84 toàn cầu (Kinh độ/Vĩ độ trong phạm vi hình học trái đất)
        elif (-180 <= c0_min <= 180) and (-90 <= c1_min <= 90):
            return "WGS84", {"X": "Longitude (X)", "Y": "Latitude (Y)", "Z": "Ellipsoid H", "ID": "ID"}
            
        else:
            return "Tọa độ giả định", {"X": "X (Local)", "Y": "Y (Local)", "Z": "Z (Z-Level)", "ID": "STT"}
    except Exception:
        return "Tọa độ giả định", {"X": "X", "Y": "Y", "Z": "Z", "ID": "ID"}

def compute_convex_hull(points_2d):
    """Xây dựng đa giác ranh giới ngoài cùng theo phương thức Convex Hull"""
    if len(points_2d) < 3:
        return points_2d
    hull = ConvexHull(points_2d)
    hull_points = points_2d[hull.vertices]
    # Nối điểm cuối trùng điểm đầu để khép kín vòng ranh hình học
    hull_points = np.vstack([hull_points, hull_points[0]])
    return hull_points
