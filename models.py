class Attraction:
    def __init__(self, name, code, coordinates, description, price=None, link=None):
        self.name = name
        self.code = code
        self.coordinates = coordinates
        self.description = description
        self.price = price  # 新增
        self.link = link  # 新增

    def __repr__(self):
        return f"{self.name} ({self.code}), 坐标: {self.coordinates}, 描述: {self.description}"



class Path:
    def __init__(self, from_attraction, to_attraction, origin, destination, distance, duration, strategy):
        self.from_attraction = from_attraction
        self.to_attraction = to_attraction
        self.origin = origin
        self.destination = destination
        self.distance = int(distance)
        self.duration = int(duration)
        self.strategy = strategy


    def __repr__(self):
        return f"{self.from_attraction} 到 {self.to_attraction}, 距离: {self.distance}m, 用时: {self.duration}s, 策略: {self.strategy}"

class BusPath:
    def __init__(self, from_attraction, to_attraction, origin, destination, distance, duration, taxi_cost, bus_cost, walking_distance, bus_name,huanchen):
        self.from_attraction = from_attraction
        self.to_attraction = to_attraction
        self.origin = origin
        self.destination = destination
        self.distance = distance
        self.duration = duration
        self.taxi_cost = taxi_cost
        self.bus_cost = bus_cost
        self.walking_distance = walking_distance
        self.bus_name = bus_name
        self.huanchen = huanchen

    def __repr__(self):
        return f"{self.from_attraction} 到 {self.to_attraction}, 距离: {self.distance}m, 用时: {self.duration}s, 出租车费用: {self.taxi_cost}元, 公交费用: {self.bus_cost}元,步行距离: {self.walking_distance}m, 公交线路: {self.bus_name},换乘次数：{self.huanchen}"