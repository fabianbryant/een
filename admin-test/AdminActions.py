import csv
from datetime import datetime
from getpass import getpass
from queue import Empty, Full, Queue
from threading import Thread
from time import sleep
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    InvalidSelectorException as InvalidSelector,
    NoSuchElementException as NotFound,
    StaleElementReferenceException as StaleReference,
    TimeoutException as Timeout,
)
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait as Wait


class AdminActions(object):
    def __init__(self, creds: dict, options: Optional[Options], shared_queue: Queue):
        # Set login credentials
        self.creds = creds

        # Create webdriver
        self.driver = webdriver.Chrome(options=options)

        # Setup I/O queues
        self.search_queue = Queue(maxsize=20)  # In-Queue
        self.shared_queue = shared_queue  # Out-Queue

        # Create searcher thread
        self.thread = Thread(target=self.search, args=(self,), daemon=True)

    def login(self):
        login_attempts = 0

        # Loop for attempting log in to Admin
        while login_attempts <= 3:
            login_attempts += 1

            # Raise exception at max attempts
            while login_attempts == 3:
                raise MaximumAttemptsException

            # GET Admin website
            self.driver.get("https://eenadmin.eagleeyenetworks.com")

            # Return if logged in
            try:
                Wait(self.driver, 3).until(
                    ec.visibility_of_element_located((By.NAME, "search_type"))
                )
            except Timeout:
                pass
            else:
                return

            # Find login elements
            try:
                usrn = Wait(self.driver, 6).until(
                    ec.visibility_of_element_located((By.NAME, "username"))
                )
                pw = Wait(self.driver, 3).until(
                    ec.visibility_of_element_located((By.NAME, "password"))
                )
            except Timeout:
                continue

            # Submit login credentials
            try:
                usrn.clear()
                usrn.send_keys(self.creds["username"])
                pw.clear()
                pw.send_keys(self.creds["password"], Keys.RETURN)
            except (NotFound, StaleReference):
                continue

            auth_attempts = 0

            # Loop for attempting authentication
            while auth_attempts < 3:
                auth_attempts += 1

                # Break loop if no auth element
                try:
                    auth = Wait(self.driver, 3).until(
                        ec.visibility_of_element_located((By.NAME, "totp"))
                    )
                except Timeout:
                    break

                # Prompt user for auth code
                try:
                    auth.clear()
                    auth.send_keys(
                        input("\nEnter authentication code: "), Keys.RETURN, Keys.RETURN
                    )
                except StaleReference:
                    continue

                # Return if login successful
                try:
                    Wait(self.driver, 3).until(
                        ec.visibility_of_element_located((By.NAME, "search_type"))
                    )
                except Timeout:
                    continue
                else:
                    return

    def search(self, serial: str):
        # Initialize search attempts
        search_attempts = 0

        # Search loop for searcher thread
        while search_attempts <= 10:
            search_attempts += 1

            # Pause and reset attempts after 10 fails
            while search_attempts == 10:
                sleep(2.5)
                search_attempts = 1
                continue

            # Check search queue for bridge serials
            try:
                serial = self.search_queue.get()
            except Empty():
                sleep(0.5)
                continue

            # Loop for ensuring user is logged in
            while True:
                try:
                    self.login()
                except MaximumAttemptsException:
                    print("\nFailed to login! Re-enter login credentials to retry.")
                    self.creds["username"] = input("\nUsername: ")
                    self.creds["password"] = getpass("Password: ")
                    continue
                else:
                    break

            # Select "Bridges and Cameras"
            try:
                Select(Wait(self.driver, 5).until(
                    ec.visibility_of_element_located((By.NAME, "search_type"))
                )).select_by_visible_text("Bridges and Cameras")
            except Timeout:
                self.search_queue.put(serial)
                continue

            # Search Admin
            try:
                search = self.driver.find_element(By.NAME, "search")
                search.clear()
                search.send_keys(serial, Keys.RETURN)
            except (NotFound, StaleReference):
                self.search_queue.put(serial)
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
                self.shared_queue.put_nowait((attach_id, serial))
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

        print("...Ready! Enter one or more bridge serials at a time.\n")

        # Loop for bridge serials
        while True:
            serial = input().upper()

            if (serial[0:6] == "EEN-BR" and len(serial) == 16) \
                    or (serial[0:5] == "MX-BR" and len(serial) == 15):
                try:
                    self.search_queue.put(serial)
                except Full:
                    continue
                else:
                    continue

            print(f"\n'{serial}' does not match proper format: \
                    'EEN-BRXXX-XXXXXX' or 'MX-BRXXX-XXXXXX' \n")
            continue

    def set_creds(self, creds: dict):
        self.creds = creds


class MaximumAttemptsException(Exception):
    def __init__(self, message="Maximum attempts exceeded!"):
        self.message = message
        super().__init__(self.message)


def main():
    print("\nEnter EEN Admin login credentials.")
    creds = {"username": input("\nUsername: "),
             "password": getpass("Password: ")}
    opts = Options()
    opts.add_argument("--headless")

    shared_queue = Queue(maxsize=20)

    admin = AdminActions(creds, opts, shared_queue)

    while True:
        try:
            print("\nAttempting login...")
            admin.login()
        except MaximumAttemptsException:
            print("\nFailed to login! Re-enter login credentials to retry.")
            creds["username"] = input("\nUsername: ")
            creds["password"] = getpass("Password: ")
            admin.set_creds(creds)
            continue
        else:
            print("\nLogin successful!\n")
            del creds
            break

    admin.start()


if __name__ == "__main__":
    main()
