from flask import Flask, render_template, request, jsonify
from functions import load_attractions, load_paths, find_polylines_in_file, calculate_distance, load_paths_v2
from ToGPS import batch_gcj02_to_wgs84

app = Flask(__name__)

# 加载景点和路径数据
attractions = load_attractions('data/attractions_summary.txt')
walk_paths = load_paths('data/walk.txt', attractions)
drive_paths = load_paths('data/drive.txt', attractions)
bus_paths1 = load_paths_v2('data/bus_quick.txt', attractions)


@app.route('/')
def index():
    return render_template('index.html')


# 返回所有景点信息
@app.route('/attractions', methods=['GET'])
def get_attractions():
    attractions_list = [
        {'name': attr.name, 'lat': float(attr.coordinates.split(',')[0]), 'lon': float(attr.coordinates.split(',')[1]),
         'description': attr.description}
        for attr in attractions.values()
    ]
    return jsonify(attractions_list)


# 查询特定景点
@app.route('/attractions/<string:name>', methods=['GET'])
def get_attraction(name):
    attraction = next((attr for attr in attractions.values() if name in attr.name), None)

    if attraction:
        return jsonify({
            'name': attraction.name,
            'code': attraction.code,
            'description': attraction.description,
            'price': attraction.price,
            'link': attraction.link,
            'lat': float(attraction.coordinates.split(',')[0]),
            'lon': float(attraction.coordinates.split(',')[1]),
        })
    else:
        return jsonify({"message": "未找到该景点。"}), 404


# 计算最优路径
@app.route('/optimal_path', methods=['POST'])
def optimal_path():
    data = request.json
    start_name = data.get('start')
    end_name = data.get('end')
    mode = data.get('mode')
    midpoints_input = data.get('midpoints')
    midpoints_names = midpoints_input if midpoints_input else []
    bus_mode = data.get('busMode')  # 获取公交方案

    start_code = None
    end_code = None
    mid_codes = []

    for attr in attractions.values():
        if attr.name == start_name:
            start_code = attr.code
        elif attr.name == end_name:
            end_code = attr.code
        elif attr.name in midpoints_names:
            mid_codes.append(attr.code)

    if not start_code or not end_code:
        return jsonify({'error': '起点或终点景点不存在'}), 404

    path_list = None
    file_path = None
    bus_info = {}

    if mode == 'walk':
        path_list = walk_paths
        file_path = 'data/walk_2.0.txt'
        color_mode = mode
    elif mode == 'drive':
        path_list = drive_paths
        file_path = 'data/drive_road.txt'
        color_mode = mode
    elif mode == 'bus':
        color_mode = mode
        if bus_mode == 'economic':
            bus_paths = load_paths_v2('data/bus_eco.txt', attractions)
            file_path = 'data/bus_road_eco.txt'
        elif bus_mode == 'fewestTransfers':
            bus_paths = load_paths_v2('data/bus_hc.txt', attractions)
            file_path = 'data/bus_road_hc.txt'
        elif bus_mode == 'fewestWalks':
            bus_paths = load_paths_v2('data/bus_fw.txt', attractions)
            file_path = 'data/bus_road_fw.txt'
        elif bus_mode == 'quick':
            bus_paths = load_paths_v2('data/bus_quick.txt', attractions)
            file_path = 'data/bus_road_quick.txt'

        path_list = bus_paths

        for path in bus_paths:
            if path.from_attraction.code == start_code and path.to_attraction.code == end_code:
                bus_info = {
                    'taxi_cost': path.taxi_cost,
                    'bus_cost': path.bus_cost,
                    'walking_distance': path.walking_distance,
                    'bus_name': path.bus_name,
                    'huanchen': path.huanchen
                }
                break
    elif mode == 'fast':
        wp = find_fast_path(walk_paths, start_code, end_code)
        dp = find_fast_path(drive_paths, start_code, end_code)
        bp = find_fast_path(bus_paths1, start_code, end_code)
        if wp is not None and (wp <= dp if dp is not None else True) and (wp <= bp if bp is not None else True):
            path_list = walk_paths
            file_path = 'data/walk_2.0.txt'
            color_mode = 'walk'
        elif dp is not None and (dp <= wp if wp is not None else True) and (dp <= bp if bp is not None else True):
            path_list = drive_paths
            file_path = 'data/drive_road.txt'
            color_mode = 'drive'
        elif bp is not None and (bp <= wp if wp is not None else True) and (bp <= dp if dp is not None else True):
            path_list = bus_paths1
            file_path = 'data/bus_road_quick.txt'
            color_mode = 'bus'
        else:
            return jsonify({'error': '没有找到可用的路径'}), 404



    best_path = calculate_distance(path_list, start_code, mid_codes, end_code)
    print(best_path)

    # 还原景点名称顺序
    mp_names = []
    for code in best_path:
        # 根据代码查找对应的名称
        if code in attractions:
            mp_names.append(attractions[code].name)  # 添加景点名称
        else:
            mp_names.append(None)  # 如果未找到，可以选择添加 None

    print(mp_names)  # 打印还原的景点名称序列

    full_path = []
    total_duration = 0
    total_distance = 0

    current_start = start_code
    for mid_code in best_path:
        path = find_path(path_list, current_start, mid_code)

        full_path.extend(path['coordinates'])
        total_duration += int(path['duration'])
        total_distance += int(path['distance'])

        polylines_points = find_polylines_in_file(file_path, current_start, mid_code)
        wgs84_coordinates = batch_gcj02_to_wgs84(polylines_points, coord_format="lon_lat")
        data_to_insert = [{'lat': polyline[1], 'lon': polyline[0]} for polyline in wgs84_coordinates]

        for point in data_to_insert:
            full_path.insert(-1, point)

        current_start = mid_code

    response = {
        'path': full_path,
        'duration': total_duration,
        'distance': total_distance,
        'waypoints': [start_name] + mp_names ,
        'color': 'red' if color_mode == 'bus' else 'green' if color_mode == 'walk' else 'blue',
    }

    if bus_info:
        response.update(bus_info)  # 将公交信息添加到响应中

    return jsonify(response)



def find_path(path_list, start, end):
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

def find_fast_path(path_list, start, end):
    for path in path_list:
        if path.from_attraction.code == start and path.to_attraction.code == end:
            return int(path.duration)
    return None

if __name__ == '__main__':
    app.run(debug=True)
