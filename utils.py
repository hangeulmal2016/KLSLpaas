import pandas as pd
import numpy as np
from scipy.spatial import ConvexHull

def parse_txt_to_df(uploaded_file):
    content = uploaded_file.getvalue().decode("utf-8")
    lines = content.strip().split('\n')
    sep = ',' if ',' in content else ('\t' if '\t' in content else r'\s+')
    uploaded_file.seek(0)
    is_header = not lines[0].replace('.', '', 1).replace('-', '', 1).replace(' ', '', 1).replace(',', '', 1).replace('\t', '', 1).strip().isdigit()
    return pd.read_csv(uploaded_file, sep=sep, header=0 if is_header else None)

def parse_dxf_to_df(uploaded_file):
    try:
        import ezdxf
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
    except Exception: pass
    return "Tọa độ giả định", {"X": "X", "Y": "Y", "Z": "Z", "ID": "STT"}

def compute_convex_hull(points_2d):
    if len(points_2d) < 3: return points_2d
    hull = ConvexHull(points_2d)
    hull_points = points_2d[hull.vertices]
    return np.vstack([hull_points, hull_points[0]])
