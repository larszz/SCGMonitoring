#!/usr/bin/env python3
import os
import pathlib

import requests
import argparse
import matplotlib.pyplot as plt
import matplotlib.patches as mpl_patches
import time
from datetime import datetime, timedelta

from matplotlib.axes import Axes
from texttable import Texttable

import config
import factory_data
import plot_data
import values
from aggregate_type import AggregateType
from history_data import HistoryData, HistoryDataDefault
from team_standing_data import TeamStandingData

from plot_data import PlotData
from values import Category
from general_data import GeneralData
from factory_data import FactoryData, ShippingConfig

# Parse arguments
arg_parser = argparse.ArgumentParser("Plotter for Supply Chain Game Data")
arg_parser.add_argument('-d', nargs='?', type=int, help="Displayed day")
arg_parser.add_argument('-n', nargs='?', type=int, help="Number of days")
arg_parser.add_argument('-f', nargs='?', type=int, help="Frequency of refreshes in seconds")
arg_parser.add_argument('-lo', action="store_true", help="Enable logging of cash only")
arg_parser.add_argument('-ld', action="store_true", help="Disable logging")
arg_parser.add_argument('-bo', action="store_true", help="Only execute backup")
arg_parser.add_argument('-be', nargs='?', type=int, help="Execute backup every x minutes")
arg_parser.add_argument('-load-backup', action="store_true", help="Get data from backup")
args = arg_parser.parse_args()

# set values
url_login = "https://op.responsive.net/SupplyChain/SCAccess"
# max_retries = 100
# delay_retry = 15
# lastXDays: int = 30
# refreshEachSeconds: int = 60
# only_logging: bool = False
# disable_logging: bool = False

loop_start_time = datetime.now()

if args.d is not None:
    config.displayed_day = args.d

if args.n is not None:
    config.lastXDays = args.d

if args.f is not None:
    config.refreshEachSeconds = args.f

if args.lo is not None:
    config.only_logging = args.lo

if args.ld is not None:
    config.disable_logging = args.ld

if args.bo:
    config.execute_backup_only = True

if args.be:
    config.execute_backups = True
    config.backup_diff_in_minutes = args.be

if args.load_backup:
    config.load_from_backup = True


def print_line(line: str):
    ts = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    print(f"[{ts}]\t{line}")


def login(session: requests.Session):
    # Do not attempt logging in when started from backups
    if config.load_from_backup:
        print_line(f"Loading from backup, no login executed!")
        return

    # TODO: creditials
    retry_ctr: int = 0
    while retry_ctr < config.max_retries:
        try:
            r = session.post(url_login,
                             data={
                                 "id": "",
                                 "password": "",
                                 "institution": "augsburg",
                                 "ismobile": "false",
                             })
            break
        except:
            retry_ctr += 1
            print_line(
                f"Login not possible, try again in {config.delay_retry} seconds ({config.max_retries - retry_ctr} attempts left)")
            time.sleep(config.delay_retry)
    print_line("Login successful")
    return


s = requests.Session()
login(s)


def get_escaped_url_for_filesave(url: str) -> str:
    return url.replace(':', '_').replace('/', '_').replace('?', '_') + ".html"


def backup_request_response(r: requests.Response):
    file_name = get_escaped_url_for_filesave(r.url)
    root_path = values.FilePaths.website_backup_directory

    backup_dir_name = loop_start_time.strftime('%Y-%m-%d_%H-%M-%S')
    directory_path = os.path.join(root_path, backup_dir_name)

    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

    file_path = os.path.join(directory_path, file_name)

    with open(file_path, 'w') as f:
        f.write(r.text)


# if no backup folder specified, the newest backup will be used
def get_response_from_backup(url: str, backup_folder: str = None):
    file_name = get_escaped_url_for_filesave(url)
    root_path = values.FilePaths.website_backup_directory

    # try get from specific folder
    if backup_folder is not None:
        directory_path = os.path.join(root_path, backup_folder)
        if not os.path.exists(directory_path):
            raise Exception(f"Directory {directory_path} not found!")
        file_path = os.path.join(directory_path, file_name)
        if not os.path.exists(file_path):
            raise Exception(f"File {file_path} not found!")

        with open(file_path, "r") as f:
            out = f.read()
        return out

    # search all backups in reversed order to find the newest backup
    else:
        subfolders = [f.path for f in os.scandir(root_path) if f.is_dir()]
        subfolders.sort(reverse=True)
        for s in subfolders:
            file_path = os.path.join(s, file_name)
            if os.path.exists(file_path):
                with open(file_path, "r") as f:
                    out = f.read()
                return out
    return None


def execute_request(s: requests.Session, url: str, name: str, get: bool = True):
    response_status: int
    response_text: str

    if config.load_from_backup:
        response_status = 200
        response_text = get_response_from_backup(url, config.load_backup_folder)
    else:
        retry_ctr = 0
        response = None
        while retry_ctr < config.max_retries:
            try:
                if get:
                    response = s.get(url, timeout=10)
                else:
                    response = s.post(url, timeout=5)
                break
            except:
                retry_ctr += 1
                print_line(
                    f"[{name}]\tDownload not possible, try again in {config.delay_retry} seconds ({config.max_retries - retry_ctr} attempts left)")
                time.sleep(config.delay_retry)

        response_status = response.status_code
        response_text = response.text

        if config.execute_backup_only or \
                (config.execute_backups and values.latest_backup_time + timedelta(minutes=
                    config.backup_diff_in_minutes) < loop_start_time):
            backup_request_response(response)

    return response_status, response_text


# easiest point where the exact date can be seen is in factory WIP
# def get_precise_day(s: requests.Session) -> float:
#     get_plot_data(s,
#                   f"https://op.responsive.net/SupplyChain/SCPlotk?submit=plot+wip&data=WIP1",
#                   f"Calo WIP", Category.WIP)
#     for x in wip_data:
#         if len(x) > 0:
#             for y in x:
#                 if len(y.points) > 0:
#                     return y.points[-1][0]
#     return None


def get_general_data(session: requests.Session, url: str):
    response_status, response_text = execute_request(session, url, "GeneralData")

    # get cash
    cash_idx_start = response_text.index("Cash: <b>$") + len("Cash: <b>$")
    cash_idx_end = response_text.index("</b>", cash_idx_start)
    cash_text = response_text[cash_idx_start:cash_idx_end].replace(",", "")
    cash_float = float(cash_text)

    # get day
    day_idx_start = response_text.index("Day: <b>") + len("Day: <b>")
    day_idx_end = response_text.index("</b>", day_idx_start)
    day_text = response_text[day_idx_start:day_idx_end].replace(",", "")
    day_int = int(day_text)

    return GeneralData(cash_float, day_int)


def get_plot_data(session: requests.Session, url: str, name: str, category: Category):
    # get data as text
    response_status, response_text = execute_request(session, url, name)

    # check if plottable data is available
    if response_text.find("no plot:") > 0:
        # print(f"{name}: no plottable data found")
        return []
    idx_start = response_text.index("lines:[")
    idx_end = response_text.index("],", idx_start)
    sub = response_text[idx_start:idx_end]
    elements: [str] = sub.split("{label: '")
    elements.pop(0)

    data_list = []

    for e in elements:
        # get name
        data_name = e[0:e.index("'")].strip()
        if data_name == '':
            data_name = name

        # get data
        point_text = e[e.index("points:'") + len("points:'"):e.index("'},")]
        point_list = point_text.split(' ')
        ret_list = []
        ret_list = [-1] * int(len(point_list) / 2)
        for i in range(0, len(ret_list)):
            ret_list[i] = []
            ret_list[i].append(float(point_list[i * 2]))
            ret_list[i].append(float(point_list[i * 2 + 1]))

        data_list.append(PlotData(data_name, category, ret_list))

    return data_list


def set_standing_data(session: requests.Session, url: str, day: int, team_standing_data: TeamStandingData):
    # get data as text
    response_status, response_text = execute_request(session, url, f"Standing", False)

    idx_start: int = response_text.index("</thead>") + len("</thead>")
    idx_start: int = response_text.index("<tr>", idx_start) + len("<tr>")
    idx_end: int = response_text.index("</table>", idx_start)
    standings = response_text[idx_start:idx_end].split('<tr>')

    for s in standings:
        # get name
        idx_start_2 = s.index("<font>") + len("<font>")
        idx_end_2 = s.index("</font>")
        name = s[idx_start_2:idx_end_2]

        # get value
        idx_start_2 = s.index("right>$", idx_end_2) + len("right>$")
        idx_end_2 = s.index("</td>", idx_start_2)
        value = float(s[idx_start_2:idx_end_2].replace(",", ""))

        team_standing_data.add_point_to_team(name, (day, value))


def get_factory_data(session: requests.Session, url: str, name: str):
    # get data as text
    response_status, response_text = execute_request(session, url, name)

    if (response_status != 200) or response_text is None:
        return None

    fd = FactoryData()

    fd.name = name

    # capacity
    idx_start: int = response_text.index("current capacity of ") + len("current capacity of ")
    idx_end: int = response_text.index(".\n")
    fd.capacity = int(float(response_text[idx_start:idx_end]))

    # get configuration block
    idx_start = response_text.index("priority level", idx_end) + len("priority level")
    idx_start = response_text.index("<tr><td>", idx_start) + len("<tr><td>")
    idx_end = response_text.index("</table>", idx_end)

    config_text = response_text[idx_start:idx_end]
    config_split = config_text.split("<tr><td>")

    for x in config_split:

        conf = ShippingConfig()

        # target
        sta = 0
        end = x.index("</td>", sta)
        conf.target = x[sta:end]

        # shipping method
        sta = x.index("<select ", end) + len("<select ")
        if "value=truck selected" in x[sta:]:
            conf.shipping_method = "Truck"
        elif "value=mail selected" in x[sta:]:
            conf.shipping_method = "Mail"
        else:
            conf.shipping_method = "NONE SELECTED"

        # order point
        sta = x.index("</select>", end)
        sta = x.index("value=", sta) + len("value=")
        end = x.index(">", sta)
        conf.order_point = int(float(x[sta:end]))

        # order quantity
        sta = x.index("quant", end)
        sta = x.index("value=", sta) + len("value=")
        end = x.index(">", sta)
        conf.quantity = int(float(x[sta:end]))

        # priority
        sta = x.index("priority", end)
        sta = x.index("value=", sta) + len("value=")
        end = x.index(">", sta)
        conf.priority = int(float(x[sta:end]))

        fd.shipping_configs.append(conf)
    return fd


def get_factory_configuration_summary(s: requests.Session):
    # get factory data
    list_factory_data = []
    for i in range(len(values.list_of_regions)):
        list_factory_data.append(
            get_factory_data(s, f"https://op.responsive.net/SupplyChain/SCFactory?action=change&region={i + 1}",
                             values.list_of_regions[i]))

    # build table
    tab = Texttable()
    tab.set_cols_width([12, 15, 15, 15, 15, 15])
    header = []
    header.append("from/to")
    content = [header]
    for idx_region in range(len(list_factory_data)):
        header.append(values.list_of_regions[idx_region])

        line = [values.list_of_regions[idx_region]]
        for idx_target in range(len(values.list_of_regions)):
            if (list_factory_data[idx_region] is None) \
                    or (list_factory_data[idx_region].shipping_configs is None) \
                    or (len(list_factory_data[idx_region].shipping_configs) <= 0):
                line.append(values.Placeholders.empty)
            # not enough shipping methods -> error
            elif len(list_factory_data[idx_region].shipping_configs) <= idx_target:
                line.append(values.Placeholders.index_error)
            # order point == 0 -> no orders specified
            elif list_factory_data[idx_region].shipping_configs[idx_target].order_point == 0:
                line.append(values.Placeholders.empty)
            # print summary
            else:
                line.append(list_factory_data[idx_region].shipping_configs[idx_target].short_summary_only_values())
        content.append(line)

    tab.add_rows(content)
    return tab.draw()


def get_history_data(s: requests.Session):
    history_url = "https://op.responsive.net/SupplyChain/SCHistory?isAdmin=undefined"
    response_status, response_text = execute_request(s, history_url, "History")

    history = HistoryData()
    history.init_from_web_response(response_text)

    return history


def get_warehouse_summary(mods: list[HistoryDataDefault], current_day: float):
    headline = f"=============== WAREHOUSE MODIFICATIONS ==============="
    header = ["Warehouse", "Day", "Finished Day", f"Days until Finished ({int(current_day)})", "New Value"]
    output = [header]
    for x in mods:
        line = []
        line.append(x.warehouse)
        line.append(x.day)
        line.append(x.day + values.OperationValues.warehouse_investment_days)
        line.append(x.day + values.OperationValues.warehouse_investment_days - current_day)
        line.append("Opening")
        output.append(line)
    tab = Texttable()
    tab.set_cols_width([15, 15, 15, 15, 15])
    tab.set_cols_align(["l", "r", "r", "r", "c"])
    tab.add_rows(output)

    return "" + headline + "\n" + tab.draw()


def get_factory_summary(mods: list[HistoryDataDefault], current_day: float):
    headline = f"================ FACTORY MODIFICATIONS ================"
    header = ["Factory", "Day", "Finished Day", f"Days until Finished ({int(current_day)})", "New Value"]
    output = [header]
    for x in mods:
        line = []
        line.append(x.factory)
        line.append(x.day)
        line.append(x.day + values.OperationValues.factory_investment_days)
        line.append(x.day + values.OperationValues.factory_investment_days - current_day)
        line.append(int(float(x.value)))
        output.append(line)
    tab = Texttable()
    tab.set_cols_width([15, 15, 15, 15, 15])
    tab.set_cols_align(["l", "r", "r", "r", "r"])
    tab.add_rows(output)

    return "" + headline + "\n" + tab.draw()


def get_pending_orders_per_region(wip_list: list[list[PlotData]]) -> dict[str, dict[str, float]]:
    ret = {}
    if len(wip_list) > 0:
        idx = 0
        for fact in wip_list:
            ret[values.list_of_regions[idx]] = {}
            for wh in fact:

                point_tmp = wh.points[-10:-1]
                # search in list for pending orders (from the end)
                pending_quantity: float = 0.0
                for point_idx in range(len(wh.points) - 2, 0, -1):
                    if wh.points[point_idx][1] == 0:
                        break
                    pending_quantity += wh.points[point_idx][1]
                # add quantity to the right dict
                if pending_quantity > 0:
                    ret[values.list_of_regions[idx]][wh.name] = pending_quantity
            idx += 1
    return ret


def get_pending_orders_summary(wip_list: list[list[PlotData]]):
    # get the orders
    pending_orders = get_pending_orders_per_region(wip_list)

    # generate output
    headline = f"==================== ORDER SUMMARY ===================="
    header = ["from / to"]
    output = [header]
    idx = 0
    for x in pending_orders:
        line = [values.list_of_regions[idx]]
        header.append(values.list_of_regions[idx])
        wh = pending_orders[x]

        # search by region index to keep the right order
        for i in range(len(values.list_of_regions)):
            found = False
            for target in wh:
                if target == values.list_of_regions[i]:
                    found = True
                    line.append(wh[target])
                    pass
            if not found:
                line.append(values.Placeholders.empty)
        output.append(line)

        idx += 1

    tab = Texttable()
    tab.set_cols_width([12, 12, 12, 12, 12, 12])
    tab.set_cols_align(["l", "r", "r", "r", "r", "r"])
    tab.add_rows(output)

    return "" + headline + "\n" + tab.draw()


def get_pending_transport_per_region(transport_list: list[list[PlotData]], today: float) -> dict[
    str, list[tuple[float, float, float]]]:
    ret = {}
    if len(transport_list) > 0:
        idx = 0
        for region in transport_list:
            ret[values.list_of_regions[idx]] = []
            for inv in region:
                if ("Mail" not in inv.name) and ("Truck" not in inv.name):
                    continue

                # search backwards to first relevant point
                shipping_days = values.OperationValues.shipping_mail_days \
                    if "Mail" in inv.name else values.OperationValues.shipping_truck_days
                relevant_from = today - shipping_days

                start_search_from = 0
                for p_idx in range(len(inv.points) - 1, 0, -1):
                    if inv.points[p_idx][0] < relevant_from:
                        start_search_from = p_idx
                        break

                # from starting point on, register every upward change
                for reg_idx in range(start_search_from, len(inv.points) - 1):
                    if inv.points[reg_idx + 1][1] > inv.points[reg_idx][1]:
                        ret[values.list_of_regions[idx]].append((inv.points[reg_idx + 1][0],
                                                                 inv.points[reg_idx + 1][0] + shipping_days,
                                                                 inv.points[reg_idx + 1][1] - inv.points[reg_idx][1],))
            idx += 1

    return ret


def get_pending_transport_summary(transport_list: list[list[PlotData]], current_day: float) -> str:
    # get the orders
    pt = get_pending_transport_per_region(transport_list, current_day)

    # generate output
    headline = f"==================== TRANSPORT SUMMARY ===================="
    header = ["Warehouse", "Day of Order", "Day of Arrival", f"Days until Arrival ({current_day})", "Quantity"]
    output = [header]
    for r in pt:
        if len(pt[r]) <= 0:
            continue
        tmp = pt[r]

        for l in pt[r]:
            line = []
            line.append(r)
            line.append(round(l[0], 2))
            line.append(round(l[1], 2))
            line.append(round(l[1], 2) - current_day)
            line.append(round(l[2], 2))
            output.append(line)
        pass

    tab = Texttable()
    tab.set_cols_width([12, 15, 15, 20, 12])
    tab.set_cols_align(["l", "r", "r", "r", "r"])
    tab.add_rows(output)

    return "" + headline + "\n" + tab.draw()


def get_history_summary(h: HistoryData, current_day: float):
    warehouse_summary = get_warehouse_summary(h.get_pending_warehouse_modification(current_day), current_day)
    factory_summary = get_factory_summary(h.get_pending_factory_modification(current_day), current_day)


def get_and_store_current_state(s: requests.Session,
                                wip_data: list[list[PlotData]],
                                transport_data: list[list[PlotData]],
                                current_day: int):
    history = get_history_data(s)
    warehouse_summary = get_warehouse_summary(history.get_pending_warehouse_modification(current_day), current_day)
    factory_summary = get_factory_summary(history.get_pending_factory_modification(current_day), current_day)
    factory_config_summary = get_factory_configuration_summary(s)
    order_summary = get_pending_orders_summary(wip_data)
    transport_summary = get_pending_transport_summary(transport_data, current_day)

    mapping = (
        (warehouse_summary, values.FilePaths.path_warehouse_output_file),
        (factory_summary, values.FilePaths.path_factory_output_file),
        (factory_config_summary, values.FilePaths.path_factory_configuration_output_file),
        (order_summary, values.FilePaths.path_order_output_file),
        (transport_summary, values.FilePaths.path_transport_output_file),
    )

    # write to files
    for m in mapping:
        with open(m[1], 'w', newline='') as f:
            f.write(m[0])


"""
Returns True for None, empty list and list with only 0 or '0'
"""


def check_list_only_zero(l: list):
    if l is None:
        return True
    if len(l) <= 0:
        return True

    for x in l:
        if (x != 0) and (x != '0'):
            return False
    return True


""" TESTING """

""" =================================================="""
""" General Data """
last_login = datetime.now()

""" =================================================="""
""" INIT PLOTTING """
# if only logging active, only log cash of all teams
if config.only_logging:
    while True:
        # execute new login each hour
        if last_login + timedelta(hours=1) < datetime.now():
            print_line(f"Execute new login")
            last_login = datetime.now()
            s.close()
            s = requests.Session()
            login(s)

        general_data = get_general_data(s, "https://op.responsive.net/SupplyChain/SCAccess")

        print_line(f"Set standing... (Day {general_data.day})")

        tsd = TeamStandingData()

        # TODO: add teams
        """
        Add all participating teams here with their name (must match exactly, so the data from the website can be matched correctly).
        Use adding as follows:
        
        tsd.add_team("[TeamName]",
                     "[csv_path]",
                     "[csv_path_raw]",
                     "[team_color]")
        """
        set_standing_data(s, "https://op.responsive.net/SupplyChain/SCStanding", general_data.day, tsd)

        time.sleep(config.refreshEachSeconds)
        continue

""" ================================================= """
# Normal behaviour

# Init overview
figure_overview, axis_overview = plt.subplots(2, 3)
plt.show(block=False)
plt.ion()

# Init overview
figure_details, axis_details = plt.subplots(3, 5)
plt.show(block=False)
plt.ion()

initial_execution = True

while True:
    loop_start_time = datetime.now()
    # execute new login each hour
    if last_login + timedelta(hours=1) < datetime.now():
        print_line(f"Execute new login")

        last_login = datetime.now()
        s.close()
        s = requests.Session()
        login(s)

    # Output
    timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    print_line(f"Update data...")

    general_data = get_general_data(s, "https://op.responsive.net/SupplyChain/SCAccess")
    from_day: int = general_data.day - config.lastXDays

    """ GET DATA """
    # Data order: warehouse, mail, truck
    plot_demand = get_plot_data(s, "https://op.responsive.net/SupplyChain/SCPlotk?submit=plot+demand&data=DEMAND1",
                                "Demand", Category.DEMAND)
    # plot_lost_demand = get_plot_data(s,
    #                                  "https://op.responsive.net/SupplyChain/SCPlotk?submit=plot+lost+demand&data=LOST1",
    #                                  "Lost demand", Category.DEMAND)
    # plot_met_demand = get_plot_data(s,
    #                                 "https://op.responsive.net/SupplyChain/SCPlotk?submit=plot+shipments&data=SHIP1SEG1",
    #                                 "Met demand", Category.DEMAND)
    # plot_wh_1_inventory = get_plot_data(s,
    #                                     "https://op.responsive.net/SupplyChain/SCPlotk?submit=plot+inventory&data=WH1",
    #                                     "WH 1 Inventory", Category.INVENTORY)
    plot_factory_1_wip = get_plot_data(s, "https://op.responsive.net/SupplyChain/SCPlotk?submit=plot+wip&data=WIP1",
                                       "Factory 1 WIP", Category.WIP)
    plot_cash_balance = get_plot_data(s,
                                      "https://op.responsive.net/SupplyChain/SCPlotk?submit=plot+cash+balance&data=BALANCE",
                                      "Cash balance", Category.CASH)

    """ =============================================== """
    """ NEW """

    # demand
    plot_demand_raw = get_plot_data(s, "https://op.responsive.net/SupplyChain/SCPlotk?submit=plot+demand&data=DEMAND1",
                                    "Demand", Category.DEMAND)
    plot_lost_demand = get_plot_data(s,
                                     "https://op.responsive.net/SupplyChain/SCPlotk?submit=plot+lost+demand&data=LOST1",
                                     "Lost demand", Category.DEMAND)
    plot_met_demand = get_plot_data(s,
                                    "https://op.responsive.net/SupplyChain/SCPlotk?submit=plot+shipments&data=SHIP1SEG1",
                                    "Met demand", Category.DEMAND)

    num_of_regions: int = 5

    plotlist_inventory = []
    plotlist_wip = []

    for r in range(1, num_of_regions + 1):
        # inventory
        plotlist_inventory.append(get_plot_data(s,
                                                f"https://op.responsive.net/SupplyChain/SCPlotk?submit=plot+inventory&data=WH{r}",
                                                f"{values.list_of_regions[r - 1]} Inventory", Category.INVENTORY))
        # wip
        plotlist_wip.append(get_plot_data(s,
                                          f"https://op.responsive.net/SupplyChain/SCPlotk?submit=plot+wip&data=WIP{r}",
                                          f"{values.list_of_regions[r - 1]} WIP", Category.WIP))

    # sum up WIP per region
    plotlist_wip_agg_inregion = []
    for idx in range(len(plotlist_wip)):
        plotlist_wip_agg_inregion.append(
            PlotData.aggregate_plot_data_by_day(f"Total WIP {values.list_of_regions[idx]}", plotlist_wip[idx], from_day,
                                                AggregateType.SUM, False, AggregateType.LAST))

    # get total WIP
    plot_wip_total = PlotData.aggregate_plot_data_by_day("Total WIP", plotlist_wip_agg_inregion, from_day,
                                                         AggregateType.SUM, False, AggregateType.LAST)

    # get aggregated inventory per region
    plotlist_inventory_agg_inregion = []
    idx = 0
    for x in plotlist_inventory:
        plotlist_inventory_agg_inregion.append(
            PlotData.aggregate_plot_data_by_day(f"{values.list_of_regions[idx]} Total Inventory", x, from_day,
                                                aggtype_between_lists=AggregateType.SUM, x_is_matching=False,
                                                aggtype_in_list=AggregateType.MAX))
        idx += 1

    # get total inventory over all regions
    plot_inventory_agg_total = []
    plot_inventory_agg_total.append(
        PlotData.aggregate_plot_data_by_day(f"Total Inventory", plotlist_inventory_agg_inregion, from_day,
                                            aggtype_between_lists=AggregateType.SUM, x_is_matching=True))

    # get summed up demand
    plot_demand_summedup = PlotData.aggregate_plot_data_by_day(f"Total Demand", plot_demand, from_day,
                                                               AggregateType.SUM)

    # get summed up lost demand
    plot_lost_demand_summedup = PlotData.aggregate_plot_data_by_day(f"Total Lost Demand", plot_lost_demand, from_day,
                                                                    AggregateType.SUM)

    # get cumulated lost demand
    plot_lost_demand_cumulated = PlotData.cumulate_plot_data(f"Total Cumulated Lost Demand", plot_lost_demand_summedup,
                                                             from_day)

    plot_cash_balance = get_plot_data(s,
                                      "https://op.responsive.net/SupplyChain/SCPlotk?submit=plot+cash+balance&data=BALANCE",
                                      "Cash balance", Category.CASH)

    for x in plot_cash_balance:
        x.multiply_all_y()

    # general data
    general_data = get_general_data(s, "https://op.responsive.net/SupplyChain/SCAccess")

    # team standing
    tsd = TeamStandingData()

    # TODO: add teams
    """
    Add all participating teams here with their name (must match exactly, so the data from the website can be matched correctly).
    Use adding as follows:
    
    tsd.add_team("[TeamName]",
                 "[csv_path]",
                 "[csv_path_raw]",
                 "[team_color]")
    """

    set_standing_data(s, "https://op.responsive.net/SupplyChain/SCStanding", general_data.day, tsd)

    # factory data
    factory_data = get_factory_data(s, "https://op.responsive.net/SupplyChain/SCFactory?action=change&region=1", 1)
    s.close()

    """ =============================================================================================== """
    """ PLOT DATA OVERVIEW"""
    for plot_factory_x in figure_overview.get_axes():
        plot_factory_x.cla()

    figure_overview.suptitle(f"OVERVIEW "
                             f"({datetime.now().strftime('%H:%M:%S') if not config.load_from_backup else 'From Backup'}"
                             f", Tag {general_data.day})", fontsize=16)

    ### Demand
    # Whole demand in sum
    # raw
    Data00 = plot_demand_summedup
    axis_overview[0, 0].plot(Data00.get_from_day_x(from_day), Data00.get_from_day_y(from_day),
                             label=Data00.name)
    # smoothed
    smoothing_day_num = 14
    data_demand_smoothed_x, data_demand_smoothed_y = Data00.get_from_day_smoothed(from_day,
                                                                                  smoothing_day_num,
                                                                                  AggregateType.AVG)

    axis_overview[0, 0].plot(data_demand_smoothed_x,
                             data_demand_smoothed_y,
                             label=f"{Data00.name} smoothed ({smoothing_day_num}d)"
                             , color="green",
                             linestyle=":")
    axis_overview[0, 0].set_ylim([0, max(Data00.get_from_day_y(from_day)) * 1.2])
    axis_overview[0, 0].set_title(Data00.name)

    handles, labels = axis_overview[0, 0].get_legend_handles_labels()
    labels_demand = []
    labels_demand.append(f"Refreshed: {datetime.now().strftime('%H:%M:%S')}")
    labels_demand.append(f"Day: {general_data.day}")
    handles_demand = [mpl_patches.Rectangle((0, 0), 1, 1, fc="white", ec="white",
                                            lw=0, alpha=0)] * len(labels_demand)

    handles.extend(handles_demand)
    labels.extend(labels_demand)
    axis_overview[0, 0].legend(handles=handles, labels=labels, loc="best", fontsize='small')

    # Lost demand (sum)
    Data01 = plot_lost_demand_summedup

    axis_overview[0, 1].plot(Data01.get_from_day_x(from_day), Data01.get_from_day_y(from_day),
                             label=f"{Data01.name} ({Data01.get_from_day_y(from_day)[-1] if len(Data01.get_from_day_y(from_day)) > 0 else 0})",
                             color="orangered")
    axis_overview[0, 1].legend(loc="best", fontsize='small')
    axis_overview[0, 1].set_title(Data01.name)

    # Lost demand (cumulated)
    Data02 = plot_lost_demand_cumulated
    axis_overview[0, 2].plot(Data02.get_from_day_x(from_day), Data02.get_from_day_y(from_day),
                             label=f"{Data02.name} ({Data02.get_from_day_y(from_day)[-1] if len(Data02.get_from_day_y(from_day)) > 0 else 0})",
                             color="orangered")
    axis_overview[0, 2].set_ylim([0, max(Data02.get_from_day_y(from_day)) * 1.2])
    axis_overview[0, 2].legend(loc="best", fontsize='small')
    axis_overview[0, 2].set_title(Data02.name)

    # WH Inventory
    # axis_overview[1, 0].plot(plot_wh_1_inventory[0].get_from_day_x(from_day),
    #                          plot_wh_1_inventory[0].get_from_day_y(from_day),
    #                          label=f"Warehouse ({plot_wh_1_inventory[0].get_from_day_y(from_day)[-1] if len(plot_wh_1_inventory[0].get_from_day_y(from_day)) > 0 else 0})")
    # axis_overview[1, 0].plot(plot_wh_1_inventory[1].get_from_day_x(from_day),
    #                          plot_wh_1_inventory[1].get_from_day_y(from_day),
    #                          label=f"Mail ({plot_wh_1_inventory[1].get_from_day_y(from_day)[-1] if len(plot_wh_1_inventory[1].get_from_day_y(from_day)) > 0 else 0})")
    # if len(plot_wh_1_inventory) > 2:
    #     axis_overview[1, 0].plot(plot_wh_1_inventory[2].get_from_day_x(from_day),
    #                              plot_wh_1_inventory[2].get_from_day_y(from_day),
    #                              label=f"Truck ({plot_wh_1_inventory[2].get_from_day_y(from_day)[-1] if len(plot_wh_1_inventory[2].get_from_day_y(from_day)) > 0 else 0})")
    #
    # axis_overview[1, 0].legend()
    axis_overview[1, 0].set_title("WH Inventory")

    # Factory WIP
    Data11 = plot_wip_total

    plot_factory_x, plot_factory_y = plot_factory_1_wip[0].get_from_day_aggregated_by_day(from_day, AggregateType.LAST,
                                                                                          fill_up_missing_days_between=True)

    axis_overview[1, 1].bar(Data11.get_from_day_x(from_day), Data11.get_from_day_y(from_day), width=1.0)
    axis_overview[1, 1].set_ylim([0, max(Data11.get_from_day_y(from_day)) + 100])
    axis_overview[1, 1].set_title(Data11.name)

    handles2 = [mpl_patches.Rectangle((0, 0), 1, 1, fc="white", ec="white", lw=0, alpha=0)] * 5
    labels_wip = []
    # labels_wip.append(f"Current Capacity: {factory_data.capacity}")
    # labels_wip.append(f"Current WIP: {plot_factory_1_wip[0].get_from_day_y(from_day)[-1]}")
    # labels_wip.append(f"Order point: {factory_data.order_point}")
    # labels_wip.append(f"Quantity: {factory_data.quantity1}")
    # labels_wip.append(f"Shipping method: {factory_data.shipping_method}")
    # axis_overview[1, 1].legend(handles=handles2, labels=labels_wip, loc="best", fontsize='small')

    # Cash Balance
    axis_overview[1, 2].plot(plot_cash_balance[0].get_from_day_x(from_day),
                             plot_cash_balance[0].get_from_day_y(from_day),
                             label=f"Current Cash: {f'{general_data.cash:,}'}", color="red")
    a2 = plot_cash_balance[0].get_from_day_x(from_day)
    a1 = plot_cash_balance[0].get_from_day_y(from_day)

    for t in tsd.teams:
        x, y = tsd.teams[t].get_datapoints_seperated(from_day)
        axis_overview[1, 2].plot(x, y, label=t, color=tsd.teams[t].color)

    # put legend below the chart
    box = axis_overview[1, 2].get_position()
    axis_overview[1, 2].set_position([box.x0, box.y0 + (box.height * 0.1 if initial_execution else 0),
                                      box.width, box.height * (0.90 if initial_execution else 1)])
    axis_overview[1, 2].legend(loc='upper center', bbox_to_anchor=(0.5, -0.1),
                               fancybox=True, shadow=True, ncol=5, fontsize='x-small')

    axis_overview[1, 2].set_title("Cash balance")

    for i in range(2):
        for j in range(3):
            axis_overview[i, j].grid(color='darkgrey')
            axis_overview[i, j].grid(color='darkgrey')
            # axis_overview[i, j].grid(which='major', alpha=0.1, color='darkgrey')
            # axis_overview[i, j].grid(which='minor', alpha=0.1, color='darkgrey')

    """ =============================================================================================== """
    """ PLOT DETAIL DATA """
    for plot_factory_x in figure_details.get_axes():
        plot_factory_x.cla()

    figure_details.suptitle(f"DETAILS "
                            f"({datetime.now().strftime('%H:%M:%S') if not config.load_from_backup else 'From Backup'}"
                            f", Tag {general_data.day})", fontsize=16)

    # get max demand for equal formatting of graphs
    max_demand: int = 0
    for i in range(num_of_regions):
        region_max = max(plot_demand[i].get_from_day_y(from_day) + plot_lost_demand[i].get_from_day_y(from_day))
        if region_max > max_demand:
            max_demand = region_max
    max_demand *= 1.2

    for i in range(num_of_regions):
        # first row: demands
        axis_details[0, i].plot(plot_demand[i].get_from_day_x(from_day), plot_demand[i].get_from_day_y(from_day),
                                label="Plain", color=plot_demand[i].color)
        # smoothed
        smoothing_day_num = 14
        data_demand_smoothed_x, data_demand_smoothed_y = plot_demand[i].get_from_day_smoothed(from_day, smoothing_day_num,
                                                                                              AggregateType.AVG)
        axis_details[0, i].plot(data_demand_smoothed_x, data_demand_smoothed_y, label=f"Smoothed({smoothing_day_num}d)", color="green",
                                linestyle=":")
        axis_details[0, i].plot(plot_lost_demand[i].get_from_day_x(from_day),
                                plot_lost_demand[i].get_from_day_y(from_day), label="Lost", color="orange")
        # axis_details[0, i].set_ylim([0, max_demand])
        axis_details[0, i].set_xlim([from_day, general_data.day])

        axis_details[0, i].set_title(f"Demand {plot_demand[i].name}")
        axis_details[0, i].legend(fontsize="small")

        # second row: inventory
        if len(plotlist_inventory[i]) > 0:
            max_y = 0

            # axis_details[1, i].plot(plotlist_inventory_agg_inregion[i].get_from_day_x(from_day),
            #                         plotlist_inventory_agg_inregion[i].get_from_day_y(from_day),
            #                         label=f"Total ({plotlist_inventory_agg_inregion[i].get_from_day_y(from_day)[-1] if len(plotlist_inventory_agg_inregion[i].get_from_day_y(from_day)) > 0 else 0})",
            #                         linestyle="--",
            #                         color="grey")

            # mail inventory
            axis_details[1, i].plot(plotlist_inventory[i][1].get_from_day_x(from_day),
                                    plotlist_inventory[i][1].get_from_day_y(from_day),
                                    label=f"Mail ({plotlist_inventory[i][1].get_from_day_y(from_day)[-1] if len(plotlist_inventory[i][1].get_from_day_y(from_day)) > 0 else 0})",
                                    color="orange")
            max_y = max(max_y, max(plotlist_inventory[i][1].get_from_day_y(from_day)) if len(
                plotlist_inventory[i][1].get_from_day_y(from_day)) > 0 else 0)

            if len(plotlist_inventory[i]) > 2:
                # if available: Truck inventory
                axis_details[1, i].plot(plotlist_inventory[i][2].get_from_day_x(from_day),
                                        plotlist_inventory[i][2].get_from_day_y(from_day),
                                        label=f"Truck ({plotlist_inventory[i][2].get_from_day_y(from_day)[-1] if len(plotlist_inventory[i][2].get_from_day_y(from_day)) > 0 else 0})",
                                        color="green")
                max_y = max(max_y, max(plotlist_inventory[i][2].get_from_day_y(from_day)) if len(
                    plotlist_inventory[i][2].get_from_day_y(from_day)) > 0 else 0)

            # actual inventory in warehouse
            axis_details[1, i].plot(plotlist_inventory[i][0].get_from_day_x(from_day),
                                    plotlist_inventory[i][0].get_from_day_y(from_day),
                                    label=f"Warehouse ({plotlist_inventory[i][0].get_from_day_y(from_day)[-1] if len(plotlist_inventory[i][0].get_from_day_y(from_day)) > 0 else 0})",
                                    color="blue")
            max_y = max(max_y, max(plotlist_inventory[i][0].get_from_day_y(from_day)) if len(
                plotlist_inventory[i][0].get_from_day_y(from_day)) > 0 else 0)

            axis_details[1, i].legend(fontsize="small")
            axis_details[1, i].set_ylim([0, max_y * 1.5])
            axis_details[1, i].set_xlim([from_day, general_data.day + 1])

        axis_details[1, i].set_title(f"Inventory {plot_demand[i].name}")

    # third row: inventory
    # get y dim of all WIPs
    y_range = 0
    for pl in plotlist_wip:
        for pd in pl:
            y_tmp = pd.get_from_day_y(from_day)
            max_y = max(y_tmp) if len(y_tmp) > 0 else 0
            max_range = max(max_y, y_range)

            y_range = max_range
    y_range *= 1.5

    # show data
    for pl_idx in range(len(plotlist_wip)):
        plotted = False
        for pd in plotlist_wip[pl_idx]:
            x_vals, y_vals = pd.get_from_day_aggregated_by_day(from_day, AggregateType.LAST, True)
            if not check_list_only_zero(y_vals):
                plotted = True
                axis_details[2, pl_idx].bar(x_vals, y_vals, width=1.0, color=pd.color, label=pd.name)
        axis_details[2, pl_idx].set_title(f"Total WIP {values.list_of_regions[pl_idx]}")
        axis_details[2, pl_idx].set_ylim([0, y_range])

        box = axis_details[2, pl_idx].get_position()
        axis_details[2, pl_idx].set_position([box.x0, box.y0 + (box.height * 0.1 if initial_execution else 0),
                                              box.width, box.height * (0.90 if initial_execution else 1)])

        # Put a legend below current axis
        if plotted:
            axis_details[2, pl_idx].legend(loc='upper center', bbox_to_anchor=(0.5, 1),
                                           fancybox=True, shadow=True, ncol=5, fontsize='x-small')

    # Set grid for all sub plots
    for i in range(3):
        for j in range(5):
            axis_details[i, j].grid(color='darkgrey')
            axis_details[i, j].grid(color='darkgrey')

    initial_execution = False

    if config.execute_backups \
            and values.latest_backup_time + timedelta(minutes=config.backup_diff_in_minutes) < loop_start_time:
        print_line(f"Backup executed!")
        values.latest_backup_time = datetime.now()

    if config.execute_backup_only:
        print_line(f"Executed backup. Exiting.")
        exit(0)

    plt.gcf().canvas.draw_idle()
    get_and_store_current_state(s, plotlist_wip, plotlist_inventory, general_data.day)

    if config.load_from_backup:
        print_line(f"Loading from backup done")
        input("Press any key to exit...")
        exit(0)

    plt.gcf().canvas.start_event_loop(config.refreshEachSeconds)
