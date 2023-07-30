import time
import requests

import values

# set values
url_login = "https://op.responsive.net/SupplyChain/SCAccess"
max_retries = 100
delay_retry = 15
lastXDays: int = 30
refreshEachSeconds: int = 60


# TODO: credentials
def login(session: requests.Session):
    r = None
    retry_ctr: int = 0
    while retry_ctr < max_retries:
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
            print(f"Login not possible, try again in {delay_retry} seconds ({max_retries - retry_ctr} attempts left)")
            time.sleep(delay_retry)
    print("login successful")
    return r


def get_response_text(session: requests.Session, url: str, get: bool):
    response = None
    retry_ctr = 0
    while retry_ctr < max_retries:
        try:
            if get:
                response = session.get(url, timeout=10)
            else:
                response = session.post(url, timeout=10)
            break
        except:
            retry_ctr += 1
            print(
                f"[Standing] Download not possible, try again in {delay_retry} seconds ({max_retries - retry_ctr} attempts left)")
            time.sleep(delay_retry)

    return response.text

pairs = [
    ('Demand', 'https://op.responsive.net/SupplyChain/SCPlotk?submit=plot+demand&data=DEMAND1', True),
    ('DemandLost', 'https://op.responsive.net/SupplyChain/SCPlotk?submit=plot+lost+demand&data=LOST1', True),
    ('Shipments', 'https://op.responsive.net/SupplyChain/SCPlotk?submit=plot+shipments&data=SHIP1SEG1', True),
    ('Inventory', 'https://op.responsive.net/SupplyChain/SCPlotk?submit=plot+inventory&data=WH1', True),
    ('WIP', 'https://op.responsive.net/SupplyChain/SCPlotk?submit=plot+wip&data=WIP1', True),
    ('Cash', 'https://op.responsive.net/SupplyChain/SCPlotk?submit=plot+cash+balance&data=BALANCE', True),
    ('GeneralData', 'https://op.responsive.net/SupplyChain/SCAccess', True),
    ('Standing', 'https://op.responsive.net/SupplyChain/SCStanding', False),
    ('FactoryData', 'https://op.responsive.net/SupplyChain/SCFactory?action=change&region=1', True),
]



s = requests.Session()

login(s)

for x in pairs:
    text = get_response_text(s, x[1], x[2])
    path = f"{values.file_backup_path}{x[0]}.html"
    with open(path, 'w', newline='') as f:
        f.write(text)
