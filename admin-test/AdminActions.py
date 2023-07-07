import time
import csv

from datetime import datetime
from queue import Queue, Empty, Full
from threading import Thread
from typing import Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.select import Select
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.wait import WebDriverWait as Wait
from selenium.webdriver.support import expected_conditions as ec
from selenium.common.exceptions import (
    TimeoutException as Timeout,
    NoSuchElementException as NotFound,
    InvalidSelectorException as InvalidSelector,
    StaleElementReferenceException as StaleReference,
)


class AdminActions(object):
    def __init__(self, options: Optional[Options]):
        # Create webdriver
        self.driver = webdriver.Chrome(executable_path="/usr/bin/chromedriver", options=options)

        # Create I/O queues
        self.in_q = Queue(maxsize=20)
        self.out_q = Queue(maxsize=20)

        # Create searcher thread
        self.thread = Thread(target=self.search, args=(self,), daemon=True)

    def login(self, username: str, password: str):
        login_attempts = 0

        # Loop for attempting log in to Admin
        while login_attempts < 11:
            
            login_attempts += 1

            # Pause and reset attempts after 10 fails
            while login_attempts == 10:
                time.sleep(2.5)
                login_attempts = 1
                continue

            # Get Admin website
            self.driver.get("https://eenadmin.eagleeyenetworks.com")

            # If logged in, break loop
            try:
                Wait(self.driver, 2.5).until(
                    ec.visibility_of_element_located((By.NAME, "search_type"))
                )
            except Timeout:
                pass
            else:
                break

            # Find login elements
            try:
                usrn = Wait(self.driver, 5).until(
                    ec.visibility_of_element_located((By.NAME, "username"))
                )
                pw = Wait(self.driver, 2.5).until(
                    ec.visibility_of_element_located((By.NAME, "password"))
                )
            except Timeout:
                continue

            # Send login credentials
            try:
                usrn.clear()
                usrn.send_keys(username)
                pw.clear()
                pw.send_keys(password, Keys.RETURN)
            except (NotFound, StaleReference):
                continue

            # Loop for attempting authentication
            auth_attempts = 0
            
            while auth_attempts < 5:
                try:
                    auth = Wait(self.driver, 2.5).until(
                        ec.visibility_of_element_located((By.NAME, "totp"))
                    )
                except Timeout:
                    break

                try:
                    auth.clear()
                    auth.send_keys(
                        input("\nEnter authentication code: "), Keys.RETURN, Keys.RETURN
                    )
                except StaleReference:
                    continue

                auth_attempts += 1

    def search(self, serial: str):
        search_attempts = 0

        # Search loop for searcher thread
        while search_attempts < 11:
            
            search_attempts += 1

            # Pause and reset attempts after 10 fails
            while search_attempts == 10:
                time.sleep(2.5)
                search_attempts = 1
                continue

            # Check search queue for bridge serials
            try:
                serial = self.in_q.get()
            except Empty():
                time.sleep(0.5)
                continue

            # Make sure user is logged in
            self.login("username", "password")

            # Select "Bridges and Cameras"
            try:
                Select(Wait(self.driver, 5).until(
                    ec.visibility_of_element_located((By.NAME, "search_type"))
                )).select_by_visible_text("Bridges and Cameras")
            except Timeout:
                self.in_q.put(serial)
                continue

            # Search Admin
            try:
                search = self.driver.find_element(By.NAME, "search")
                search.clear()
                search.send_keys(serial, Keys.RETURN)
            except (NotFound, StaleReference):
                self.in_q.put(serial)
                continue

            # Inform user if no results
            try:
                Wait(self.driver, 2.5).until(
                    ec.visibility_of_element_located((By.XPATH, ".//p[contains(text(), 'No matches.')]"))
                )
            except (Timeout, InvalidSelector):
                pass
            else:
                print(f"\nNo matches found for '{serial}'.\n")
                continue

            # Retrieve and print bridge data
            try:
                ip_addr = Wait(self.driver, 5).until(
                    ec.visibility_of_element_located((By.XPATH, "//td[@id='bridge-ip_address']"))
                ).text
            except (Timeout, InvalidSelector):
                continue
            else:
                serial = self.driver.find_element(By.XPATH, "//td[@id='bridge-serial']").text
                attach_id = self.driver.find_element(By.XPATH, "//td[@id='bridge-connect_id']").text
                firmware = self.driver.find_element(By.XPATH, "//td[@id='bridge-firmware']").text

                print(f"\nIP: {ip_addr} | Serial: {serial}"
                      f"\nAttach ID: {attach_id} | Firmware: {firmware}\n")

            # Put relevant data into outbound queue
            try:
                self.out_q.put_nowait((attach_id, serial))
            except Full:
                pass

            file_name = datetime.now().strftime("%Y-%m-%d")

            # Save bridge data to CSV file
            try:
                open(file_name + ".csv", "x")
            except FileExistsError:
                pass
            else:
                with open(file_name + ".csv", "a") as csv_file:
                    writer = csv.writer(csv_file, delimiter="\t")
                    writer.writerow((serial, attach_id, firmware))

            # Reset attempts upon successful loop
            search_attempts = 0

    def start(self):
        # Start searcher thread
        self.thread.start()

        print("\n...Ready! Scan-in or enter one or more bridge serials at a time.\n")

        # Loop for bridge serials
        while True:

            serial = input().upper()

            if (serial[0:6] == "EEN-BR" and len(serial) == 16) \
                    or (serial[0:5] == "MX-BR" and len(serial) == 15):
                try:
                    self.in_q.put(serial)
                except Full:
                    continue
                else:
                    continue

            print(f"\n'{serial}' does not match proper format: 'EEN-BRXXX-XXXXXX' or 'MX-BRXXX-XXXXXX' \n")
            continue


def main():
    options = Options()
    options.add_argument("--headless")
    admin = AdminActions(options)
    admin.login("username", "password")
    admin.start()


if __name__ == "__main__":
    main()
