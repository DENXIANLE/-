import re
from models import Attraction, Path,BusPath
from ToGPS import gcj02_to_wgs84
import itertools

def load_attractions(file_path):
    attractions = {}

    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            # 去除首尾空白并按逗号分割
            parts = line.strip().split(',')
            if len(parts) == 7:  # 确保有六个部分
                name = parts[0].strip()
                code = parts[1].strip()
                
                # 获取括号内的坐标和描述
                
                lat = parts[2].strip().strip("(")
                lon = parts[3].strip().strip(")")
                
                description = parts[4].strip().strip("'")  # 去掉单引号
                price = parts[5].strip().strip("'")  # 去掉单引号
                link = parts[6].strip().strip("'")  # 去掉单引号

                attractions[code] = Attraction(name, code, f"{lat}, {lon}", description,price,link)
            else:
                print(f"Error parsing line: {line.strip()}")
    
    return attractions



def load_paths(file_path, attractions):
    paths = []
    path_pattern = re.compile(
        r"(.+)\((.+)\) to (.+)\((.+)\), \{'origin': '(.+)', 'destination': '(.+)', 'distance': '(\d+)', 'duration': '(\d+)', 'strategy': (.+)\}")

    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            match = path_pattern.match(line.strip())
            if match:
                from_name, from_code, to_name, to_code, origin1, destination1, distance, duration, strategy = match.groups()
                strategy = strategy if strategy != 'None' else None
                from_attraction = attractions.get(from_code.strip())
                to_attraction = attractions.get(to_code.strip())
                if from_attraction and to_attraction:
                    origin_lon, origin_lat=map(float, origin1.split(','))
                    destination_lon, destination_lat = map(float, destination1.split(','))
                    converted_origin_lon, converted_origin_lat = gcj02_to_wgs84(origin_lon, origin_lat)
                    converted_destination_lon, converted_destination_lat = gcj02_to_wgs84(destination_lon,destination_lat)

                    # 保证转换后的经纬度格式与原始数据相同，保留6位小数
                    origin = f"{converted_origin_lon:.6f},{converted_origin_lat:.6f}"
                    destination = f"{converted_destination_lon:.6f},{converted_destination_lat:.6f}"
                    paths.append(
                        Path(from_attraction, to_attraction, origin, destination, distance, duration, strategy))
    return paths




def load_paths_v2(file_path, attractions):
    paths = []
    path_pattern = re.compile(
        r"(.+)\((.+)\) to (.+)\((.+)\), \{'origin': '(.+)', 'destination': '(.+)', 'distance': '(\d+)', 'duration': '(\d+)', 'taxi_cost': '(\d+)', 'bus_cost': '([\d.]+)', 'walking_distance': '(\d+)', 'bus_name': '(.+)', 'huanchen': (\d+)\}")

    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            match = path_pattern.match(line.strip())
            if match:
                (from_name, from_code, to_name, to_code, origin1, destination1, distance, duration,
                 taxi_cost, bus_cost, walking_distance, bus_name, huanchen) = match.groups()

                from_attraction = attractions.get(from_code.strip())
                to_attraction = attractions.get(to_code.strip())

                if from_attraction and to_attraction:
                    # 将经纬度转换为浮点数并执行坐标转换
                    origin_lon, origin_lat = map(float, origin1.split(','))
                    destination_lon, destination_lat = map(float, destination1.split(','))

                    converted_origin_lon, converted_origin_lat = gcj02_to_wgs84(origin_lon, origin_lat)
                    converted_destination_lon, converted_destination_lat = gcj02_to_wgs84(destination_lon, destination_lat)

                    # 保证转换后的经纬度格式与原始数据相同，保留6位小数
                    origin = f"{converted_origin_lon:.6f},{converted_origin_lat:.6f}"
                    destination = f"{converted_destination_lon:.6f},{converted_destination_lat:.6f}"

                    # 创建 BusPath 实例并添加到 paths 列表中
                    paths.append(
                        BusPath(from_attraction, to_attraction, origin, destination, distance, duration, taxi_cost, bus_cost,
                                walking_distance, bus_name, huanchen))  # 传递 huanchen 作为整数
    return paths



def find_path(path_list, start, end):
    # 查找对应的路径
    for path in path_list:
        if path.from_attraction.code == start and path.to_attraction.code == end:
            return {
                'from': path.from_attraction.name,
                'to': path.to_attraction.name,
                'coordinates': [
                    {'lat': float(path.origin.split(',')[1]), 'lon': float(path.origin.split(',')[0])},
                    {'lat': float(path.destination.split(',')[1]), 'lon': float(path.destination.split(',')[0])}
                ],
                'distance': path.distance,
                'duration': path.duration,
                'type': 'walk' if 'walk' in path_list else 'drive'
            }
    return None


def find_polylines_in_file(file_path, start_code, end_code):
    """
    逐行读取 road.txt 文件，找到起点和终点匹配的路线并返回其 polylines 坐标列表。

    :param file_path: road.txt 文件的路径
    :param start_code: 起点编码
    :param end_code: 终点编码
    :return: 匹配路线的 polylines 坐标列表，如果没有找到则返回空列表
    """
    try:
        with open(file_path, 'r') as file:
            for line in file:
                # 清除空白字符并跳过空行
                line = line.strip()
                if not line:
                    continue

                try:
                    # 将行转换为字典
                    road_data = eval(line)  # 使用 eval 解析为字典

                    # 去掉空格后比较起点和终点
                    origin = road_data.get('origin').strip()
                    destination = road_data.get('destination').strip()

                    if origin == start_code and destination == end_code:
                        # 初始化 polylines 列表
                        polylines = []

                        # 解析多段 polylines 信息并返回
                        for polyline in road_data.get('polylines', []):
                            coordinates = [tuple(map(float, point.split(','))) for point in polyline.split(';')]
                            polylines.extend(coordinates)

                        return polylines

                except Exception as e:
                    pass  # 解析失败时忽略该行并继续

    except FileNotFoundError:
        print(f"File {file_path} not found.")
    except Exception as e:
        print(f"Error while reading file: {e}")

    # 没有找到匹配的路线，返回空列表
    return []

def split_midpoints(midpoints_str):
    # 使用分号将字符串分割并去除多余空格

    midpoints_list = [midpoint.strip() for midpoint in midpoints_str.split(';')]
    return midpoints_list


# def calculate_distance(path_list, start_code, mid_codes, end_code):
#     # 将终点代码添加到中间点列表中
#     mid_codes = mid_codes + [end_code]  # 将终点也当作中间点

#     min_distance = float('inf')  # 初始化最小距离为无限大
#     best_path = []  # 存储最佳路径

#     # 遍历所有中间点的排列
#     for mid_order in itertools.permutations(mid_codes):
#         current_location = start_code  # 将起点设为提供的起点
#         total_distance = 0
#         full_path = [start_code]  # 存储路径的完整顺序

#         # 遍历中间点顺序
#         for mid_code in mid_order:
#             path = find_path(path_list, current_location, mid_code)
#             if path:
#                 total_distance += int(path['distance'])  # 累加距离
#                 full_path.append(mid_code)  # 加入路径
#                 current_location = mid_code  # 更新当前位置
#             else:
#                 total_distance = float('inf')  # 如果路径不存在，则设为无穷大
#                 break  # 终止当前排列的计算

#         # 不再需要重新查找终点路径，因为它已经包含在中间点中

#         # 更新最小距离和最佳路径
#         if total_distance < min_distance:
#             min_distance = total_distance
#             best_path = full_path

#     return best_path[1:]  # 返回最佳路径




def calculate_distance(path_list, start_code, mid_codes, end_code):
    mid_codes = mid_codes + [end_code]
    min_distance = float('inf')
    best_path = []

    # 缓存已计算路径
    path_cache = {}

    # 计算起点到每个中间点的最短路径
    def get_path_distance(start, end):
        if (start, end) in path_cache:
            return path_cache[(start, end)]
        path = find_path(path_list, start, end)
        distance = int(path['distance']) if path else float('inf')
        path_cache[(start, end)] = distance
        return distance

    for mid_order in itertools.permutations(mid_codes):
        current_location = start_code
        total_distance = 0
        full_path = [start_code]

        for mid_code in mid_order:
            distance = get_path_distance(current_location, mid_code)
            if distance != float('inf'):
                total_distance += distance
                full_path.append(mid_code)
                current_location = mid_code
                # 提前终止当前路径的计算，如果超出已知最小距离
                if total_distance >= min_distance:
                    break
            else:
                total_distance = float('inf')
                break

        if total_distance < min_distance:
            min_distance = total_distance
            best_path = full_path

    return best_path[1:]



if __name__ == '__main__':
    pass