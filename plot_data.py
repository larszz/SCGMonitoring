import config
import plot_data
from aggregate_type import AggregateType
from values import Category


class PlotData:
    category: Category
    name: str
    points: list[tuple]
    color: str = "blue"

    def __init__(self, name, category, points, capitalize: bool = True):
        self.name = name
        self.category = category
        self.points = points
        self.color = self.get_default_color(name)

        if capitalize:
            self.name = self.name.capitalize()

    def get_x(self):
        ret = []
        for i in range(len(self.points)):
            ret.append(self.points[i][0])
        return ret

    def get_from_day_points(self, from_day: int):
        i = 0
        points = sorted(self.points, key=lambda l: l[0])
        for i in reversed(range(len(points))):
            if points[i][0] < from_day:
                i += 1
                break
        return points[i:]

    def get_from_day_aggregated_by_day(self,
                                       from_day: int,
                                       aggregate_type: AggregateType,
                                       fill_up_missing_days_between: bool = False
                                       ):
        points = self.get_from_day_points(from_day)
        x = []
        y = []
        idx = 0

        if len(points) <= 0:
            x = range(from_day, from_day + config.lastXDays + 1)
            y = [0] * (config.lastXDays + 1)

        else:
            while idx < len(points):
                day = round(points[idx][0])
                val = points[idx][1]
                idx += 1

                # fill up missing days
                if fill_up_missing_days_between:
                    last_day = from_day if len(x) < 1 else x[-1] + 1
                    last_value = 0 if len(x) <= 0 else y[-1]
                    while day > last_day:
                        x.append(last_day)
                        y.append(last_value)
                        last_day += 1

                # get max value of day
                if aggregate_type == AggregateType.MAX:
                    while (idx < len(points)) and (day == round(points[idx][0])):
                        if points[idx][1] > val:
                            val = points[idx][1]
                        idx += 1

                # get min value of day
                elif aggregate_type == AggregateType.MIN:
                    while (idx < len(points)) and (day == round(points[idx][0])):
                        if points[idx][1] < val:
                            val = points[idx][1]
                        idx += 1

                # get last value of day
                elif aggregate_type == AggregateType.LAST:
                    while (idx < len(points)) and (day == round(points[idx][0])):
                        val = points[idx][1]
                        idx += 1

                # default: average
                else:
                    counter: int = 1
                    while (idx < len(points)) and (day == round(points[idx][0])):
                        val += points[idx][1]
                        counter += 1
                        idx += 1
                    val = val / counter

                x.append(day)
                y.append(val)

        return x, y

    def get_from_day_smoothed(self, from_day: int, num_of_smoothing_days: int, aggregate_type: AggregateType):
        points = self.get_from_day_aggregated_by_day(max(from_day - num_of_smoothing_days, 0), aggregate_type)
        x = []
        y = []

        for i in range(len(points[0])):
            idx_start = max(0, i - round((num_of_smoothing_days - 1) / 2))
            idx_end = min(len(points[0]) - 1, i + round((num_of_smoothing_days - 1) / 2))
            point_sum = sum(x for x in points[1][idx_start:idx_end])
            point_len = idx_end - idx_start
            val = point_sum / point_len
            if points[0][i] >= from_day:
                x.append(points[0][i])
                y.append(val)

        return x, y

    def get_from_day_x(self, from_day: int):
        points = self.get_from_day_points(from_day)
        ret = []
        for x in points:
            ret.append(x[0])
        return ret

    def get_from_day_y(self, from_day: int):
        points = self.get_from_day_points(from_day)
        ret = []
        for x in points:
            ret.append(x[1])
        return ret

    def get_y(self):
        ret = []
        if len(self.points) <= 0:
            return ret
        for i in range(len(self.points)):
            ret.append(self.points[i][1])
        return ret

    def multiply_all_y(self, mult: int = 1000):
        for i in range(len(self.points)):
            self.points[i][1] *= mult
        return self

    def __str__(self):
        return self.category.name + ": " + self.name + " (" + str(len(self.points)) + " values)"

    @staticmethod
    def get_default_color(name: str):
        default = 'y'
        if name is None:
            return default

        if "Calopeia" in name:
            return "#000000"
        elif "Sorange" in name:
            return "#ff0000"
        elif "Tyran" in name:
            return "#00ff00"
        elif "Entworpe" in name:
            return "#0000ff"
        elif "Fardo" in name:
            return "#00ffff"
        else:
            return default

    @staticmethod
    def aggregate_plot_data_by_day(new_name: str, data: list, from_day: int,
                                   aggtype_between_lists: AggregateType = AggregateType.AVG, x_is_matching: bool = True,
                                   aggtype_in_list: AggregateType = AggregateType.AVG):
        aggregated_x = []
        aggregated_y = []

        y_values: list = []
        points = []
        if len(data) > 0:
            # x
            if x_is_matching:
                aggregated_x = data[0].get_from_day_x(from_day)
            else:
                x_agg, y_agg = data[0].get_from_day_aggregated_by_day(from_day, aggtype_in_list, True)
                aggregated_x = x_agg

            # y
            for d in data:
                if x_is_matching:
                    y_values.append(d.get_from_day_y(from_day))
                else:
                    x_agg, y_agg = d.get_from_day_aggregated_by_day(from_day, aggtype_in_list, True)
                    y_values.append(y_agg)

            if len(y_values) > 0:
                aggregated_y = PlotData.aggregate_lists_by_index(y_values, aggtype_between_lists)

            if len(aggregated_x) != len(aggregated_y):
                return PlotData(new_name, "AGGREGATE", [], False)

            for i in range(len(aggregated_x)):
                points.append((aggregated_x[i], aggregated_y[i]))

        return PlotData(new_name, "AGGREGATE", points, False)

    """
    Needed formats:
    data_lists: [[int, int], [int, int], [int, int]]; every sub-list has to have the same length
    """

    @staticmethod
    def aggregate_lists_by_index(data_list: list, aggtype: AggregateType = AggregateType.AVG):
        ret_values = []
        for day_idx in range(len(data_list[0])):
            val_y: float = 0.0

            if aggtype == AggregateType.MAX:
                for list_idx in range(len(data_list)):
                    if len(data_list[list_idx]) > day_idx:
                        if data_list[list_idx][day_idx] > val_y:
                            val_y = data_list[list_idx][day_idx]
                ret_values.append(val_y)

            elif aggtype == AggregateType.MIN:
                val_y = float("inf")
                for list_idx in range(len(data_list)):
                    if len(data_list[list_idx]) > day_idx:
                        if data_list[list_idx][day_idx] < val_y:
                            val_y = data_list[list_idx][day_idx]
                ret_values.append(val_y)

            elif aggtype == AggregateType.SUM:
                for list_idx in range(len(data_list)):
                    if len(data_list[list_idx]) > day_idx:
                        val_y += data_list[list_idx][day_idx]
                ret_values.append(val_y)

            else:
                counter = 0
                for list_idx in range(len(data_list)):
                    if len(data_list[list_idx]) > day_idx:
                        counter += 1
                        val_y += data_list[list_idx][day_idx]
                ret_values.append(0 if counter == 0 else val_y / counter)

        return ret_values

    @staticmethod
    def cumulate_plot_data(new_name: str, pd, from_day: int):
        points = []
        x_vals, y_vals = pd.get_from_day_aggregated_by_day(0, AggregateType.AVG, True)
        if (len(x_vals) == len(y_vals)) and (len(x_vals) > 0):
            points.append((x_vals[0], y_vals[0]))
            last_y = y_vals[0]
            for i in range(1, len(x_vals)):
                points.append((x_vals[i], last_y + y_vals[i]))
                last_y = last_y + y_vals[i]

        return PlotData(new_name, "CUMULATED", points[from_day:], False)
