import csv

import config


class TeamStandingData:
    teams: dict = {}
    own_team: str = "" #TODO: fill out own team name so it's not logged twice

    def __init__(self):
        self.teams = {}
    """
    Team_values has to be in form of (team_name, csv_path)
    """
    def add_team(self, team_name: str, csv_path: str, csv_path_raw: str, color: str):
        td = TeamData(team_name, csv_path, csv_path_raw, color).init_from_csv()
        self.teams[team_name] = td
        return self

    def add_point_to_team(self, team_name: str, point: ()):
        if not team_name == self.own_team:
            self.teams[team_name].add_data_point(point)



class TeamData:
    name: str
    datapoints: list
    csv_path: str
    csv_path_raw: str
    color: str

    def __init__(self, name: str, csv_path: str, csv_path_raw: str, color: str):
        self.name = name
        self.datapoints = []
        self.csv_path = csv_path
        self.csv_path_raw = csv_path_raw
        self.color = color


    def init_from_csv(self):
        with open(self.csv_path, 'r') as f:
            reader = csv.reader(f, delimiter=',')
            for row in reader:
                self.datapoints.append((float(row[0]), float(row[1])))
            self.datapoints = self.get_averaged_datapoints()
        return self


    def add_data_point(self, point: tuple):
        if not config.load_from_backup:
            self.datapoints.append(point)
            self.datapoints = self.get_averaged_datapoints()
            self.write_to_csv(self.csv_path, self.datapoints)
            self.write_to_csv_raw(self.csv_path_raw, point)


    def add_multiple_data_points(self, points: list):
        if not config.load_from_backup:
            for x in points:
                self.datapoints.append(x)
                self.write_to_csv_raw(self.csv_path_raw, x)
            self.datapoints = self.get_averaged_datapoints()
            self.write_to_csv(self.csv_path, self.datapoints)


    def get_averaged_datapoints(self):
        datapoints_sorted = sorted(self.datapoints,key=lambda l:l[0])
        datapoints_result = []

        idx: int = 0
        while idx < len(datapoints_sorted):
            day: int = datapoints_sorted[idx][0]
            sum: int = datapoints_sorted[idx][1]
            counter: int = 1
            idx += 1

            while (idx < len(datapoints_sorted)) and (day == datapoints_sorted[idx][0]):
                sum += datapoints_sorted[idx][1]
                idx += 1
                counter += 1

            avg: float = float(sum) / counter if counter > 0 else sum
            datapoints_result.append((day, avg))

        return datapoints_result

    def get_datapoints_seperated(self, from_day: int):
        x: list = []
        y: list = []

        idx = len(self.datapoints)-1
        while idx >= 0 and self.datapoints[idx][0] >= from_day:
            x.append(self.datapoints[idx][0])
            y.append(self.datapoints[idx][1])
            idx -= 1
        return x,y

    @staticmethod
    def write_to_csv(path: str, data: []):
        if config.disable_logging:
            return
        with open(path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(data)


    @staticmethod
    def write_to_csv_raw(path: str, point: tuple):
        if config.disable_logging:
            return
        # out = f"{point[0]}, {point[1]}"
        with open(path, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(point)
