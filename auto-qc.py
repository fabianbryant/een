import sys
import csv
import time
import queue
# ~ import logging
import threading

from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait as Wait, Select
from selenium.common.exceptions import (
    NoSuchElementException as NotFoundErr,
    TimeoutException as TimeoutErr,
    StaleElementReferenceException as StaleRefErr,
    InvalidSelectorException as SelectorErr,
    ElementClickInterceptedException as InterceptErr,
)

# ~ Last updated 5/21/23
# ~ Need to add: logging, thread + function for finding/adding cameras in Viewer,
# ~ Code still needs to be tested at QC Station
# ~ Version of this code w/o Queues or Threads is used at QC currently

"""
Program was scripted by Fabian Bryant, Manufacturing Technician. (fbryant@een.com)
This program was created to automate repetitive tasks at the QC station and increase unit throughput.
"""


def getAdmin():
    """
    Gets EEN Admin using Webdriver 1.
    :return:
    """

    tries = 0

    while tries < 11:
        tries += 1

        while tries == 10:
            time.sleep(2.5)
            tries = 1
            continue

        wd1.get("https://eenadmin.eagleeyenetworks.com")

        try:
            Wait(wd1, 2.5).until(
                ec.visibility_of_element_located((By.NAME, "search_type"))
            )
        except (NotFoundErr, TimeoutErr, StaleRefErr, SelectorErr):
            pass
        else:
            break

        try:
            usr = Wait(wd1, 7.5).until(
                ec.visibility_of_element_located((By.NAME, "username"))
            )
        except (NotFoundErr, TimeoutErr, StaleRefErr, SelectorErr):
            continue
        else:
            usr.send_keys(USERNAME)
            while True:
                cont = input(
                    "\nEnter 'ok' when login is authenticated to continue: "
                ).lower()
                if cont == "ok":
                    break
                print("\nGot invalid response:", str(cont), "\n")
                continue
            break


def getViewer(acct):
    """
    Gets Eagle Eye Viewer using Webdriver 2.
    :return:
    """

    tries = 0

    while tries < 11:
        tries += 1

        while tries == 10:
            time.sleep(2.5)
            tries = 1
            continue

        wd2.get("https://c014.eagleeyenetworks.com/#/dash")

        try:
            Wait(wd2, 2.5).until(ec.presence_of_element_located((By.NAME, "search")))
        except (NotFoundErr, TimeoutErr, StaleRefErr, SelectorErr):
            pass
        else:
            break

        try:
            usr = Wait(wd2, 7.5).until(
                ec.visibility_of_element_located((By.ID, "email"))
            )
        except (NotFoundErr, TimeoutErr, StaleRefErr, SelectorErr):
            continue
        else:
            usr.clear()
            usr.send_keys(acct)
            pwd = wd2.find_element(By.ID, "password1")
            pwd.clear()
            pwd.send_keys(PASSWORD)
            wd2.find_element(By.ID, "login_button").click()
            break


def searcher(in_q, out_q):
    """
    Search function to be used by Thread 1.
    :return:
    """

    tries = 0

    while tries < 11:
        tries += 1

        while tries == 10:
            time.sleep(2.5)
            tries = 1
            continue

        try:
            serial = in_q.get()
        except queue.Empty():
            time.sleep(0.5)
            continue

        getAdmin()

        try:
            Select(
                Wait(wd1, 5).until(
                    ec.visibility_of_element_located((By.NAME, "search_type"))
                )
            ).select_by_visible_text("Bridges and Cameras")
        except (NotFoundErr, TimeoutErr, StaleRefErr, SelectorErr):
            in_q.put(serial)
            continue
        else:
            srch = wd1.find_element(By.NAME, "search")
            srch.clear()
            srch.send_keys(serial, Keys.RETURN)

        try:
            Wait(wd1, 2.5).until(
                ec.visibility_of_element_located(
                    (By.XPATH, ".//p[contains(text(), 'No matches.')]")
                )
            )
        except (NotFoundErr, TimeoutErr, StaleRefErr, SelectorErr):
            pass
        else:
            in_q.put(serial)
            continue

        try:
            ip = Wait(wd1, 5).until(
                    ec.visibility_of_element_located(
                        (By.XPATH, "//td[@id='bridge-ip_address']")
                    )
                ).text
        except (NotFoundErr, TimeoutErr, StaleRefErr, SelectorErr):
            continue
        else:
            serial = wd1.find_element(By.XPATH, "//td[@id='bridge-serial']").text
            attach_id = wd1.find_element(By.XPATH, "//td[@id='bridge-connect_id']").text
            firmware = wd1.find_element(By.XPATH, "//td[@id='bridge-firmware']").text

            if not attach_id:
                wd1.get(
                    "https://eenadmin.eagleeyenetworks.com/eenadmin/vms_admin/vms/manufactureddevice/"
                )

                try:
                    search = Wait(wd1, 5).until(
                        ec.visibility_of_element_located((By.NAME, "q"))
                    )
                except (NotFoundErr, TimeoutErr, StaleRefErr, SelectorErr):
                    in_q.put(serial)
                    continue
                else:
                    search.clear()
                    search.send_keys(serial, Keys.RETURN)

                try:
                    pgn = Wait(wd1, 5).until(
                            ec.visibility_of_element_located(
                                (By.XPATH, "//p[@class='paginator']")
                            )
                        ).text
                except (NotFoundErr, TimeoutErr, StaleRefErr, SelectorErr):
                    in_q.put(serial)
                    continue
                else:
                    if pgn[0] == "0":
                        print("\nNo bridges found for:", serial, "\n")
                        continue

                    elif pgn[0] == "1":
                        ip = "None"
                        serial = wd1.find_element(
                            By.XPATH, "//td[@class='field-serialNumber']"
                        ).text
                        attach_id = wd1.find_element(
                            By.XPATH, "//td[@class='field-activationCode']"
                        ).text
                        firmware = "None"

                    else:
                        print("\nFound multiple bridges for:", serial, "\n")
                        continue
        finally:
            print(
                "\n\t\t",
                ip,
                "\n\n\t\t",
                serial,
                "\n\n\t\t",
                attach_id,
                "\n\n\t\t",
                firmware,
                "\n",
            )

        out_q.put((attach_id, serial))

        row = (serial, attach_id, firmware)

        file_name = datetime.now().strftime("%Y-%m-%d")

        try:
            open(file_name + ".csv", "x")
        except FileExistsError:
            pass
        else:
            with open(file_name + ".csv", "a") as csv_file:
                writer = csv.writer(csv_file, delimiter="\t")
                writer.writerow(row)
        tries = 0


def connecter(out_q):
    """
    Connect function to be used by Thread 2.
    :return:
    """

    getViewer(acct)

    tries = 0

    while tries < 11:
        tries += 1

        while tries == 10:
            time.sleep(2.5)
            tries = 1
            continue

        try:
            bridge = out_q.get()
        except queue.Empty:
            time.sleep(0.5)
            continue

        getViewer(acct)

        try:
            Wait(wd2, 5).until(
                ec.visibility_of_element_located(
                    (By.XPATH, "//div[@class='btn-group device-dropdown-menu']")
                )
            ).click()
        except (NotFoundErr, TimeoutErr, StaleRefErr, SelectorErr, InterceptErr):
            bridge.put(out_q)
            continue

        try:
            Wait(wd2, 5).until(
                ec.visibility_of_element_located(
                    (By.XPATH, ".//a[contains(text(), 'Add Bridge')]")
                )
            ).click()
        except (NotFoundErr, TimeoutErr, StaleRefErr, SelectorErr, InterceptErr):
            bridge.put(out_q)
            continue

        try:
            bridge_id = Wait(wd2, 5).until(
                ec.visibility_of_element_located(
                    (By.XPATH, "//input[@id='addBridgeConnectID']")
                )
            )
        except (NotFoundErr, TimeoutErr, StaleRefErr, SelectorErr):
            bridge.put(out_q)
            continue
        else:
            bridge_id.clear()
            bridge_id.send_keys(bridge[0])
            bridge_name = wd2.find_element(By.XPATH, "//input[@id]='addBridgeName']")
            bridge_name.clear()
            bridge_name.send_keys(bridge[1], Keys.TAB, Keys.TAB, Keys.RETURN)
        tries = 0


def main():
    getAdmin()
    getViewer()

    t1 = threading.Thread(target=searcher, name="Thread 1", args=(in_q, out_q,), daemon=True)
    t1.start()

    t2 = threading.Thread(target=connecter, name="Thread 2", args=(out_q,), daemon=True)
    t2.start()

    print("\nScan or enter bridge serials."
         "\nMultple serials can be copy/pasted from spreadsheet at one time, also.")

    while True:
        x = input().upper()

        if (x[0:6] == "EEN-BR") and (len(x) == 16):
            try:
                in_q.put(x)
            except queue.Full:
                continue
            else:
                continue

        print("\n", x, "does not match proper format: EEN-BRXXX-XXXXXX\n")
        continue


while True:
    option = input(
        "\nWhich Eagle Eye Viewer account will be used?"
        "\n1. ACCOUNT  OR  2. ACCOUNT2  [ACC/ACC2]: "
    ).upper()

    if option == 1 or "SUT":
        acct = ACCOUNT
        break

    elif option == 2 or "SUT2":
        acct = ACCOUNT2
        break

    print("\nGot invalid response:", str(option), "\n")
    continue

# ~ options = webdriver.FirefoxOptions()
# ~ options.add_argument("--headless")

wd1 = webdriver.Firefox()
wd2 = webdriver.Firefox()

in_q = queue.Queue()
out_q = queue.Queue()

main()
