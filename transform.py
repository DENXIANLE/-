import sqlite3
import re
from tqdm import tqdm

def init_database():
    """初始化数据库结构（包含坐标转换支持）"""
    conn = sqlite3.connect('attractions.db')
    cursor = conn.cursor()
    
    # 创建景点表（增强版）
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS attractions(
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        lng REAL NOT NULL CHECK(lng BETWEEN -180 AND 180),
        lat REAL NOT NULL CHECK(lat BETWEEN -90 AND 90),
        description TEXT,
        ticket_info TEXT,
        url TEXT
    )''')
    
    # 创建路线表（支持多交通模式）
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS routes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        origin_id TEXT NOT NULL,
        dest_id TEXT NOT NULL,
        mode TEXT CHECK(mode IN ('bus', 'drive', 'walk')) NOT NULL,
        strategy TEXT CHECK(strategy IN ('eco', 'fw', 'hc', NULL)),
        distance INTEGER CHECK(distance > 0),
        duration INTEGER CHECK(duration > 0),
        cost REAL CHECK(cost >= 0),
        bus_name TEXT,
        transfers INTEGER CHECK(transfers >= 0),
        FOREIGN KEY (origin_id) REFERENCES attractions(id),
        FOREIGN KEY (dest_id) REFERENCES attractions(id)
    )''')
    
    # 创建路径点表（支持轨迹存储）
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS path_points (
        route_id INTEGER NOT NULL,
        seq INTEGER CHECK(seq >= 0),
        lng REAL NOT NULL,
        lat REAL NOT NULL,
        FOREIGN KEY (route_id) REFERENCES routes(id),
        PRIMARY KEY (route_id, seq)
    )''')
    
    # 创建加速索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_routes_main ON routes(origin_id, dest_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_path_points ON path_points(route_id)')
    
    conn.commit()
    return conn

class DataLoader:
    def __init__(self, conn):
        self.conn = conn
        self.cursor = conn.cursor()
        self.coord_cache = {}  # 坐标转换缓存
        
    def _convert_coord(self, lng, lat):
        """坐标转换逻辑（示例实现）"""
        # 此处应替换为实际的gcj02_to_wgs84实现
        return lng, lat  # 示例直接返回原始坐标

    def load_attractions(self, file_path):
        """加载景点数据（增强版）"""
        pattern = re.compile(r'''
            ^([^,]+?),        # 景点名称
            ([A-Z0-9]{4,}),   # 景点编码
            \(([\d.]+),       # 经度
            ([\d.]+)\),       # 纬度
            '([^']*)',        # 描述
            '([^']*)',        # 票价信息
            '([^']*)'         # 官网链接
        ''', re.X)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in tqdm(f, desc='加载景点数据'):
                match = pattern.match(line.strip())
                if not match: continue
                
                name, code, lng, lat, desc, price, url = match.groups()
                conv_lng, conv_lat = self._convert_coord(float(lng), float(lat))
                
                self.cursor.execute('''
                    INSERT OR REPLACE INTO attractions 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (code, name, conv_lng, conv_lat, desc, price, url))
        
        self.conn.commit()
    
    def _parse_path_line(self, line):
        """通用路径解析方法"""
        base_pattern = re.compile(r'''
            (.+?)\(([A-Z0-9]+)\)\s+to\s+   # 起点
            (.+?)\(([A-Z0-9]+)\)\s*,\s*    # 终点
            \{([^}]+)\}                    # 属性字典
        ''', re.X)
        
        match = base_pattern.match(line.strip())
        if not match: return None
        
        from_name, from_code, to_name, to_code, props_str = match.groups()
        props = {}
        
        # 解析属性字典
        for pair in props_str.split(','):
            key, value = pair.split(':', 1)
            props[key.strip(" '")] = value.strip(" '")
        
        return {
            'from_code': from_code,
            'to_code': to_code,
            'props': props
        }
    
    def load_routes(self, file_path, mode):
        """加载路线数据（支持多模式）"""
        strategy_map = {
            'bus_eco.txt': 'eco',
            'bus_fw.txt': 'fw',
            'bus_hc.txt': 'hc'
        }
        
        # 确定策略类型
        strategy = strategy_map.get(file_path.split('/')[-1]) if mode == 'bus' else None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in tqdm(f, desc=f'加载{mode}数据'):
                data = self._parse_path_line(line)
                if not data: continue
                
                # 解析坐标
                origin_lng, origin_lat = map(float, data['props']['origin'].split(','))
                dest_lng, dest_lat = map(float, data['props']['destination'].split(','))
                
                # 插入路线
                self.cursor.execute('''
                    INSERT INTO routes (
                        origin_id, dest_id, mode, strategy,
                        distance, duration, cost, bus_name, transfers
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    data['from_code'],
                    data['to_code'],
                    mode,
                    strategy,
                    int(data['props']['distance']),
                    int(data['props']['duration']),
                    self._parse_cost(data['props'], mode),
                    data['props'].get('bus_name'),
                    int(data['props'].get('huanchen', 0)) if mode == 'bus' else 0
                ))
                
                # 插入路径点
                route_id = self.cursor.lastrowid
                if 'polylines' in data['props']:
                    points = [
                        tuple(map(float, p.split(','))) 
                        for p in data['props']['polylines'].split(';')
                    ]
                    for seq, (lng, lat) in enumerate(points):
                        conv_lng, conv_lat = self._convert_coord(lng, lat)
                        self.cursor.execute('''
                            INSERT INTO path_points 
                            VALUES (?, ?, ?, ?)
                        ''', (route_id, seq, conv_lng, conv_lat))
        
        self.conn.commit()
    
    def _parse_cost(self, props, mode):
        """统一费用解析逻辑"""
        cost_map = {
            'bus': lambda p: float(p.get('bus_cost', 0)),
            'drive': lambda p: float(p.get('taxi_cost', 0)),
            'walk': lambda _: 0.0
        }
        return cost_map[mode](props)
    
def main():
    # 初始化数据库
    conn = init_database()
    loader = DataLoader(conn)
    
    try:
        # 加载景点数据
        loader.load_attractions('data\\attractions_summary.txt')
        
        # 加载不同交通方式数据
        transport_modes = [
            ('data\\bus_eco.txt', 'bus'),
            ('data\\bus_fw.txt', 'bus'),
            ('data\\bus_hc.txt', 'bus'),
            ('data\\drive.txt', 'drive'),
            ('data\walk.txt', 'walk')
        ]
        
        for file_path, mode in transport_modes:
            loader.load_routes(file_path, mode)
            
    finally:
        conn.close()

def test():
    conn = sqlite3.connect('attractions.db')
    cursor = conn.cursor()
    
    # 查询景点  
    cursor.execute('SELECT COUNT (*) FROM attractions;')
    print(cursor.fetchone())

if __name__ == '__main__':
    main()
    test()


    