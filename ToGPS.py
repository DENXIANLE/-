import math

# 定义常量
PI = 3.14159265358979324
A = 6378245.0  # 长半轴
EE = 0.00669342162296594323  # 扁率

# 判断坐标是否在中国境内
def out_of_china(lon, lat):
    if lon < 72.004 or lon > 137.8347:
        return True
    if lat < 0.8293 or lat > 55.8271:
        return True
    return False

# 转换经度
def transform_lon(lon, lat):
    ret = 300.0 + lon + 2.0 * lat + 0.1 * lon * lon + 0.1 * lon * lat + 0.1 * math.sqrt(abs(lon))
    ret += (20.0 * math.sin(6.0 * lon * PI) + 20.0 * math.sin(2.0 * lon * PI)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lon * PI) + 40.0 * math.sin(lon / 3.0 * PI)) * 2.0 / 3.0
    ret += (150.0 * math.sin(lon / 12.0 * PI) + 300.0 * math.sin(lon / 30.0 * PI)) * 2.0 / 3.0
    return ret

# 转换纬度
def transform_lat(lon, lat):
    ret = -100.0 + 2.0 * lon + 3.0 * lat + 0.2 * lat * lat + 0.1 * lon * lat + 0.2 * math.sqrt(abs(lon))
    ret += (20.0 * math.sin(6.0 * lon * PI) + 20.0 * math.sin(2.0 * lon * PI)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lat * PI) + 40.0 * math.sin(lat / 3.0 * PI)) * 2.0 / 3.0
    ret += (160.0 * math.sin(lat / 12.0 * PI) + 320.0 * math.sin(lat / 30.0 * PI)) * 2.0 / 3.0
    return ret

# GCJ-02 to WGS-84
def gcj02_to_wgs84(lon, lat):
    if out_of_china(lon, lat):
        return lon, lat
    d_lat = transform_lat(lon - 105.0, lat - 35.0)
    d_lon = transform_lon(lon - 105.0, lat - 35.0)
    rad_lat = lat / 180.0 * PI
    magic = math.sin(rad_lat)
    magic = 1 - EE * magic * magic
    sqrt_magic = math.sqrt(magic)
    d_lat = (d_lat * 180.0) / ((A * (1 - EE)) / (magic * sqrt_magic) * PI)
    d_lon = (d_lon * 180.0) / (A / sqrt_magic * math.cos(rad_lat) * PI)
    mg_lat = lat + d_lat
    mg_lon = lon + d_lon
    return lon * 2 - mg_lon, lat * 2 - mg_lat

# 批量转换函数，支持(经度, 纬度)和(纬度, 经度)两种输入
def batch_gcj02_to_wgs84(coordinates, coord_format="lon_lat"):
    """
    将一组GCJ-02坐标转换为WGS-84坐标。

    参数:
    coordinates (list of tuples): GCJ-02坐标列表，格式为 (lon, lat) 或 (lat, lon)。
    coord_format (str): 输入的坐标格式，'lon_lat' 表示 (经度, 纬度)，'lat_lon' 表示 (纬度, 经度)。

    返回:
    list of tuples: WGS-84坐标列表，格式与输入格式一致。
    """
    if coord_format == "lon_lat":
        return [gcj02_to_wgs84(lon, lat) for lon, lat in coordinates]
    elif coord_format == "lat_lon":
        return [tuple(reversed(gcj02_to_wgs84(lon, lat))) for lat, lon in coordinates]
    else:
        raise ValueError("Invalid coord_format. Use 'lon_lat' or 'lat_lon'.")

# 示例调用
if __name__ == "__main__":
    # 示例输入：GCJ-02坐标列表 (经度, 纬度)
    gcj02_coordinates_lon_lat = [
        (108.963798, 34.217977),
        (108.963798, 34.21753),
        (108.963802, 34.217435),
    ]

    # 示例输入：GCJ-02坐标列表 (纬度, 经度)
    gcj02_coordinates_lat_lon = [
        (34.218285, 108.964162),
        (34.212717, 108.974360),
        (34.275848, 108.947207)
    ]

    # 批量转换为WGS-84坐标，输入格式为(经度, 纬度)
    wgs84_coordinates_lon_lat = batch_gcj02_to_wgs84(gcj02_coordinates_lon_lat, coord_format="lon_lat")
    for coord in wgs84_coordinates_lon_lat:
        print(f"WGS-84坐标 (经度, 纬度): 经度={coord[0]}, 纬度={coord[1]}")

    # 批量转换为WGS-84坐标，输入格式为(纬度, 经度)
    wgs84_coordinates_lat_lon = batch_gcj02_to_wgs84(gcj02_coordinates_lat_lon, coord_format="lat_lon")
    for coord in wgs84_coordinates_lat_lon:
        print(f"WGS-84坐标 (纬度, 经度): 纬度={coord[0]}, 经度={coord[1]}")
