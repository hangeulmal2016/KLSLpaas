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
