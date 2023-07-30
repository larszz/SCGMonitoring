import requests

from values import HistoryOperationTypes, get_history_operation_type, OperationValues
from string_helper import get_index


class HistoryDataDefault:
    day: float
    text: str
    operation: HistoryOperationTypes
    operation_text: str
    factory: str
    warehouse: str
    value: str

class HistoryData:

    all_data: list[HistoryDataDefault]
    data_by_operation: dict[HistoryOperationTypes, list[HistoryDataDefault]]

    def __init__(self):
        self.all_data = []
        self.data_by_operation = {}
        pass

    def init_data_by_operation(self):
        for d in self.all_data:
            # add key with empty list if missing
            if d.operation not in self.data_by_operation:
                self.data_by_operation[d.operation] = []
            self.data_by_operation[d.operation].append(d)
        pass

    def init_from_web_response(self, t: str):
        if t is None:
            return

        start1 = get_index(t, "</thead>")
        start1 = get_index(t, "<tr>", start1, True)
        end1 = get_index(t, "</tbody>", start1)

        history_string = t[start1:end1]
        history_string_list = history_string.split("</tr>")
        history_string_list.pop(-1)

        for x in history_string_list:
            hd = HistoryDataDefault()

            # day
            s = get_index(x, "right>", 0, True)
            e = get_index(x, "</td>", s)
            hd.day = float(x[s:e].replace(',', ''))

            # text
            s = get_index(x, "left>", e, True)
            e = get_index(x, "</td>", s)
            hd.text = x[s:e]

            # operation
            s = get_index(x, "left>", e, True)
            e = get_index(x, "</td>", s)
            hd.operation_text = x[s:e]
            hd.operation = get_history_operation_type(hd.operation_text)

            # factory
            s = get_index(x, "left>", e, True)
            e = get_index(x, "</td>", s)
            hd.factory = x[s:e]

            # warehouse
            s = get_index(x, "left>", e, True)
            e = get_index(x, "</td>", s)
            hd.warehouse = x[s:e]

            # value
            s = get_index(x, "right>", e, True)
            e = get_index(x, "</td>", s)
            hd.value = x[s:e]

            self.all_data.append(hd)

        self.init_data_by_operation()

    def get_data_from_date(self, from_date = 0):
        ret = []
        for x in self.all_data:
            if int(x.day) >= from_date:
                ret.append(x)
        return ret

    def get_data_by_operation_from_date(self, o: HistoryOperationTypes, from_date: float = 0):
        ret = []
        if o in self.data_by_operation:
            lst = self.data_by_operation[o]
            for x in lst:
                if int(x.day) >= from_date:
                    ret.append(x)
        return ret

    # Note: day is not adjusted, so it's still the day of starting, not of completion!
    def get_pending_factory_modification(self, current_day: float):
        return self.get_data_by_operation_from_date(HistoryOperationTypes.SCHEDULE_FACTORY,
                                                    current_day - OperationValues.factory_investment_days)

# Note: day is not adjusted, so it's still the day of starting, not of completion!
    def get_pending_warehouse_modification(self, current_day: float):
        return self.get_data_by_operation_from_date(HistoryOperationTypes.SCHEDULE_WAREHOUSE,
                                                    current_day - OperationValues.warehouse_investment_days)




