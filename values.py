from datetime import datetime, timedelta
from enum import Enum

list_of_regions = ["Calopeia", "Sorange", "Tyran", "Entworpe", "Fardo"]

last_day: int = 1460

latest_backup_time = datetime.now() - timedelta(days=1)

# TODO: pathes
file_backup_path = ""
txt_output_path = ""

class FilePaths:
    path_warehouse_output_file = r"outputs\warehouse_mods.txt"
    path_factory_output_file = r"outputs\factory_mods.txt"
    path_factory_configuration_output_file = r"outputs\factory_config.txt"
    path_order_output_file = r"outputs\order_pending.txt"
    path_transport_output_file = r"outputs\transport_pending.txt"

    website_backup_directory = r"website_backups_continuously"


class OperationValues:
    factory_investment_days: int = 90
    warehouse_investment_days: int = 60

    shipping_truck_days = 7
    shipping_mail_days = 1

class Category(Enum):
    CASH = 1
    DEMAND = 2
    WIP = 3
    INVENTORY = 4

class Placeholders:
    empty = "---"
    index_error = "IDX_ERR"

class HistoryOperationTypes(Enum):
    SHIPPING = 1
    SERVE_REGION = 2
    SCHEDULE_WAREHOUSE = 3
    SCHEDULE_FACTORY = 4
    FULFILLMENT_POLICY = 5
    ORDER_POINT = 6
    ORDER_QUANTITY = 7
    ORDER_PRIORITY = 8

    UNDEFINED = 99

def get_history_operation_type(type_string: str) -> HistoryOperationTypes:
    if "Shipping" in type_string:
        return HistoryOperationTypes.SHIPPING
    elif "Satisfy demand in" in type_string:
        return HistoryOperationTypes.SERVE_REGION
    elif "Schedule warehouse" in type_string:
        return HistoryOperationTypes.SCHEDULE_WAREHOUSE
    elif "Schedule capacity change" in type_string:
        return HistoryOperationTypes.SCHEDULE_FACTORY
    elif "Fulfillment policy" in type_string:
        return HistoryOperationTypes.FULFILLMENT_POLICY
    elif "Order point" in type_string:
        return HistoryOperationTypes.ORDER_POINT
    elif "Order quantity" in type_string:
        return HistoryOperationTypes.ORDER_QUANTITY
    elif "Order priority" in type_string:
        return HistoryOperationTypes.ORDER_PRIORITY
    else:
        return HistoryOperationTypes.UNDEFINED
