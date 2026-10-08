import pandas as pd
import numpy as np
from scipy.spatial import ConvexHull
import io

try:
    import ezdxf
    EZDXF_AVAILABLE = True
except ImportError:
    EZDXF_AVAILABLE = False

def parse_txt_to_df(uploaded_file):
    content = uploaded_file.getvalue().decode("utf-8")
    lines = content.strip().split('\n')
    sep = ',' if ',' in content else ('\t' if '\t' in content else r'\s+')
    uploaded_file.seek(0)
    is_header = not lines[0].replace('.', '', 1).replace('-', '', 1).replace(' ', '', 1).replace(',', '', 1).replace('\t', '', 1).strip().isdigit()
    return pd.read_csv(uploaded_file, sep=sep, header=0 if is_header else None)

def parse_dxf_to_df(uploaded_file):
    if not EZDXF_AVAILABLE: return None
    try:
        dxf_bytes = uploaded_file.getvalue().decode("utf-8", errors="ignore")
        doc = ezdxf.readstring(dxf_bytes)
        msp = doc.modelspace()
        points = []
        for p in msp.query('POINT'): points.append(p.dxf.location)
        for pl in msp.query('LWPOLYLINE'):
            for p in pl.get_points(): points.append((p[0], p[1], p[2] if len(p) > 2 else 0.0))
        return pd.DataFrame(points, columns=['X', 'Y', 'Z']) if points else None
    except Exception: return None

def detect_crs_and_headings(df):
    try:
        c0_min, c1_min = df.iloc[:, 0].min(), df.iloc[:, 1].min()
        if (100000 <= c0_min <= 3000000) and (100000 <= c1_min <= 3000000):
            return "VN2000", {"X": "North (X)", "Y": "East (Y)", "Z": "H", "ID": "ID"}
        elif (-180 <= c0_min <= 180) and (-90 <= c1_min <= 90):
            return "WGS84", {"X": "Lon (X)", "Y": "Lat (Y)", "Z": "H", "ID": "ID"}
    except Exception: pass
    return "Tọa độ giả định", {"X": "X", "Y": "Y", "Z": "Z", "ID": "STT"}

def compute_convex_hull(points_2d):
    if len(points_2d) < 3: return points_2d
    hull = ConvexHull(points_2d)
    hull_points = points_2d[hull.vertices]
    return np.vstack([hull_points, hull_points[0]])

def export_dxf_bytes(layers_dict):
    """
    layers_dict = {
       'layer_name': {'points': df, 'boundary': numpy_array, 'color_idx': int}
    }
    Mã màu AutoCAD ACAD: 1=Red, 3=Green, 5=Blue, 7=White
    """
    if not EZDXF_AVAILABLE: return b""
    doc = ezdxf.new('R2000')
    msp = doc.modelspace()
    
    for layer_name, data in layers_dict.items():
        color = data.get('color_idx', 7)
        doc.layers.new(name=layer_name, dxfattribs={'color': color})
        
        # Xuất tập điểm, số thứ tự và cao độ điểm
        df_pts = data.get('points')
        if df_pts is not None and not df_pts.empty:
            for _, row in df_pts.iterrows():
                x, y, z, p_id = row['X'], row['Y'], row['Z'], str(row['ID'])
                msp.add_point((x, y, z), dxfattribs={'layer': layer_name})
                # Xuất text cao độ lơ lửng cách điểm 1 khoảng nhỏ
                msp.add_text(f"H:{z:.2f}", dxfattribs={'layer': layer_name, 'height': 0.5}).set_pos((x + 0.5, y + 0.5, z))
                msp.add_text(f"ID:{p_id}", dxfattribs={'layer': layer_name, 'height': 0.5}).set_pos((x + 0.5, y - 0.5, z))
        
        # Xuất đường Boundary đa giác khép kín
        poly = data.get('boundary')
        if poly is not None and len(poly) > 0:
            msp.add_polyline3d(poly, dxfattribs={'layer': layer_name})
            
    out_buf = io.StringIO()
    doc.write(out_buf)
    return out_buf.getvalue().encode('utf-8')
