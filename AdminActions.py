import time
import queue
import csv

from datetime import datetime
from threading import Thread
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import Select, WebDriverWait as Wait
from selenium.common.exceptions import (
    TimeoutException as Timeout,
    NoSuchElementException as NotFound,
    InvalidSelectorException as InvalidSel
)


class AdminActions(object):
    def __init__(self):
        # Create webdriver
        self.wd = webdriver.Firefox()

        # Create search queue
        self.q = queue.Queue(maxsize=20)

        # Create searcher thread
        self.th = Thread(target=self.search, args=(self, q), daemon=True)

    def login(self):
        tries = 0

        # Loop for attempting login
        while tries < 11:
            tries += 1

            # Rest and reset attempts after 10 failed attempts
            while tries == 10:
                time.sleep(2.5)
                tries = 1
                continue

            # GET EEN Admin website
            self.wd.get("https://eenadmin.eagleeyenetworks.com")

            # Break loop if already logged in
            try:
                Wait(self.wd, 2.5).until(
                    ec.visibility_of_element_located((By.NAME, "search_type"))
                )
            except (Timeout, NotFound):
                pass
            else:
                break

            # Prompt user to manually log in
            try:
                Wait(self.wd, 7.5).until(
                    ec.visibility_of_element_located((By.NAME, "username"))
                )
            except (Timeout, NotFound):
                continue
            else:
                while True:
                    ans = input("\nLog in to EEN Admin. Enter 'ok' when logged in to continue: ").lower()
                    if ans == "ok":
                        break
                    print(f"\nGot invalid response: '{ans}' Please only enter 'ok'.\n")
                    continue
                break

    def search(self, q):
        tries = 0

        # Search loop for retrieving and handling bridge data
        while tries < 11:
            tries += 1

            # Rest and reset attempts after 10 consecutive failed attempts
            while tries == 10:
                time.sleep(2.5)
                tries = 1
                continue

            # Check search-queue and GET
            try:
                serial = self.q.get()
            except queue.Empty():
                time.sleep(0.5)
                continue

            # Make sure user is logged in
            self.login()

            # Select search-type and search
            try:
                Select(Wait(self.wd, 5).until(
                    ec.visibility_of_element_located((By.NAME, "search_type"))
                )).select_by_visible_text("Bridges and Cameras")
            except (Timeout, NotFound):
                self.q.put(serial)
                continue
            else:
                srch = self.wd.find_element(By.NAME, "search")
                srch.clear()
                srch.send_keys(serial, Keys.RETURN)

            # if no results
            try:
                Wait(self.wd, 2.5).until(
                    ec.visibility_of_element_located((By.XPATH, ".//p[contains(text(), 'No matches.')]"))
                    )
            except (Timeout, NotFound, InvalidSel):
                pass
            else:
                print(f"\nNo matches found for '{serial}'.\n")
                continue
            
            # Retrieve and display bridge data
            try:
                ip_addr = Wait(self.wd, 5).until(
                    ec.visibility_of_element_located((By.XPATH, "//td[@id='bridge-ip_address']"))
                ).text
            except (Timeout, NotFound, InvalidSel):
                continue
            else:
                serial = self.wd.find_element(By.XPATH, "//td[@id='bridge-serial']").text
                attach_id = self.wd.find_element(By.XPATH, "//td[@id='bridge-connect_id']").text
                firmware = self.wd.find_element(By.XPATH, "//td[@id='bridge-firmware']").text

                print(f"\n\t\t{ip_addr}\n\n\t\t{serial}\n\n\t\t{attach_id}\n\n\t\t{firmware}\n")

            # PUT relevant bridge data into outbound queue
            try:
                q.put_nowait((attach_id, serial))
            except queue.Full():
                pass

            # Assign CSV file name as today's date in YYYY-MM-DD format
            file_name = datetime.now().strftime("%Y-%m-%d")

            # Save relevant bridge data to CSV file
            try:
                open(file_name + ".csv", "x")
            except FileExistsError:
                pass
            else:
                with open(file_name + ".csv", "a") as csv_file:
                    writer = csv.writer(csv_file, delimiter="\t")
                    writer.writerow(serial, attach_id, firmware)

            # Reset attempts and continue
            tries = 0

    def start(self):
        # Start searcher thread
        self.th.start()

        print("\n...Ready! Scan-in or enter one or multiple bridge serials at a time.\n")
        
        # Loop for entering bridge serials for searching
        while True:
            serial = input().upper()
            if (serial[0:6] == "EEN-BR" and len(serial) == 16) or (serial[0:5] == "MX-BR" and len(serial) == 15):
                try:
                    self.q.put(serial)
                except queue.Full:
                    continue
                else:
                    continue
            print(f"\n '{serial}' does not match proper format: [ EEN-BRXXX-XXXXXX / MX-BRXXX-XXXXXX ]\n")
            continue


if __name__ == "__main__":
    admin = AdminActions()
    admin.login()
    q = queue.Queue(maxsize=1)  # Maxsize 1 b/c outbound queue is useless without ApiActions.py or ViewerActions.py
    admin.start()
