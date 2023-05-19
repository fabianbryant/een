import sys
import csv
import time
import queue
#~ import logging
import threading

from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait as Wait, Select
from selenium.common.exceptions import NoSuchElementException as NotFoundErr, \
    TimeoutException as TimeoutErr, StaleElementReferenceException as StaleRefErr, \
    InvalidSelectorException as SelectorErr, ElementClickInterceptedException as InterceptErr


#~ Last updated 5/19/23
#~ Need to add: logging, thread + function for finding/adding cameras, 

"""
Program was scripted by Fabian Bryant, Manufacturing Technician. (fbryant@een.com)
This program was created to automate QC testing procedures and increase unit throughput.
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
            time.sleep(5)
            tries = 1
            continue

        wd1.get('https://eenadmin.eagleeyenetworks.com')

        try:
            Wait(wd1, 2.5).until(
                ec.presence_of_element_located((By.NAME, 'search_type'))
            )
        except (NotFoundErr, TimeoutErr, StaleRefErr, SelectorErr):
            pass
        else:
            break

        try:
            usr = Wait(wd1, 7.5).until(
                ec.visibility_of_element_located((By.NAME, 'username'))
            )
        except (NotFoundErr, TimeoutErr, StaleRefErr, SelectorErr):
            continue
        else:
            usr.send_keys('@een.com')

            while True:
                cont = input("\nEnter 'ok' when login is authenticated to continue: ").lower()
                if cont == 'ok':
                    break
                print('\nGot invalid response:', str(cont), '\n')
                continue

        break


def getViewer(acct):

    """
    Gets Eagle Eye Viewer using Webdriver 2.
    :return:
    """

    tries = 0

    while tries <11:
        tries += 1
        
        while tries == 10:
            time.sleep(5)
            tries = 1
            continue

        wd2.get('https://c014.eagleeyenetworks.com/#/dash')

        try:
            Wait(wd2, 2.5).until(
                ec.presence_of_element_located((By.NAME, 'search'))
            )
        except (NotFoundErr, TimeoutErr, StaleRefErr, SelectorErr):
            pass
        else:
            break

        try:
            usr = Wait(wd2, 7.5).until(
                ec.visibility_of_element_located((By.ID, 'email'))
            )
        except (NotFoundErr, TimeoutErr, StaleRefErr, SelectorErr):
            continue

        try:
            usr.clear()
            usr.send_keys(acct)

            pwd = wd2.find_element(By.ID, 'password1')
            pwd.clear()
            pwd.send_keys('eagle23soaring')

            btn = wd2.find_element(By.ID, 'login_button').click()
        except (NotFoundErr, TimeoutErr, StaleRefErr, SelectorErr, InterceptErr):
            continue

        break


def searcher(in_q, out_q):

    """
    Search function to be used by Thread 1.
    :return:
    """

    getAdmin()

    tries = 0

    while tries < 11:
        tries += 1

        while tries == 10:
            time.sleep(5)
            tries = 1
            continue
        
        try:
            serial = in_q.get()
        except queue.Empty():
            time.sleep(0.5)
            continue

        getAdmin()
        
        try:
            Select(Wait(wd1, 7.5).until(
                ec.visibility_of_element_located((By.NAME, 'search_type')))
            ).select_by_visible_text('Bridges and Cameras')
        except (NotFoundErr, TimeoutErr, StaleRefErr, SelectorErr):
            in_q.put(serial)
            continue

        try:
            srch = wd1.find_element(By.NAME, 'search')
            srch.clear()
            srch.send_keys(serial)

            btn = wd1.find_element(By.ID, 'search-button').click()
        except (NotFoundErr, TimeoutErr, StaleRefErr, SelectorErr, InterceptErr):
            in_q.put(serial)
            continue

        try:
            ip = Wait(wd1, 10).until(
                ec.visibility_of_element_located((By.XPATH, "//td[@id='bridge-ip_address']"))
            ).text
        except (NotFoundErr, TimeoutErr, StaleRefErr, SelectorErr):
            in_q.put(serial)
            continue
        
        if ip == 'None':
            wd1.get('https://eenadmin.eagleeyenetworks.com/eenadmin/vms_admin/vms/manufactureddevice/')

            try:
                srch = Wait(wd1, 7.5).until(
                    ec.visibility_of_element_located(By.NAME, 'q')
                )
            except (NotFoundErr, TimeoutErr, StaleRefErr, SelectorErr):
                in_q.put(serial)
                continue

            try:
                srch.clear()
                srch.send_keys(serial, Keys.RETURN)
            except (NotFoundErr, TimeoutErr, StaleRefErr, SelectorErr):
                in_q.put(serial)
                continue

            try:
                pgn = Wait(wd1, 10).until(
					ec.visibility_of_element_located((By.XPATH, "//p[@class='paginator']"))
                ).text
            except (NotFoundErr, TimeoutErr, StaleRefErr, SelectorErr):
                in_q.put(serial)
                continue

            if pgn[0] == '0':
                in_q.put(serial)
                continue

            elif pgn[0] == '1':
                try:
                    serial = wd1.find_element(By.XPATH, "//td[@class='field-serialNumber']").text

                    attach_id = wd1.find_element(By.XPATH, "//td[@class='field-activationCode']").text

                    firmware = 'None'
                except (NotFoundErr, TimeoutErr, StaleRefErr, SelectorErr):
                    in_q.put(serial)
                    continue
                
            else:
                print('\nFound multiple bridges for:', serial, '\n')
                continue

        else:
            try:
                serial = wd1.find_element(By.XPATH, "//td[@id]='bridge-serial']").text

                attach_id = wd1.find_element(By.XPATH, "//td[@id='bridge-connect_id']").text

                firmware = wd1.find_element(By.XPATH, "//td[@id='bridge-firmware']").text
            except (NotFoundErr, TimeoutErr, StaleRefErr, SelectorErr):
                in_q.put(serial)
                continue

        print('\n\t\t' + ip, '\n\n\t\t' + serial, '\n\n\t\t' + attach_id, '\n\n\t\t' + firmware, '\n')
        
        try:
            out_q.put((attach_id, serial))
        except queue.Full:
            in_q.put(serial)
            continue

        row = [serial, attach_id, firmware]

        file_name = datetime.now().strftime('%Y-%m-%d')
        
        try:
            open(file_name + '.csv', 'x')
        except FileExistsError:
            pass

        with open(file_name + '.csv', 'a') as csv_file:
            writer = csv.writer(csv_file, delimiter='\t')
            writer.writerow(row)
        
        tries = 0

        time.sleep(0.1)


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
            time.sleep(5)
            tries = 1
            continue

        try:
            bridge = out_q.get()
        except queue.Empty:
            time.sleep(0.5)
            continue
        
        getViewer(acct)

        try:
            Wait(wd2, 7.5).until(
                ec.visibility_of_element_located((By.XPATH, "//div[@class='btn-group device-dropdown-menu']"))
            ).click()
        except (NotFoundErr, TimeoutErr, StaleRefErr, SelectorErr, InterceptErr):
            bridge.put(out_q)
            continue

        try:
            Wait(wd2, 7.5).until(
                ec.visibility_of_element_located((By.XPATH, ".//a[contains(text(), 'Add Bridge')]"))
            ).click()
        except (NotFoundErr, TimeoutErr, StaleRefErr, SelectorErr, InterceptErr):
            bridge.put(out_q)
            continue

        try:
            id = Wait(wd2, 7.5).until(
                ec.visibility_of_element_located((By.XPATH, "//input[@id='addBridgeConnectID']"))
            )
        except (NotFoundErr, TimeoutErr, StaleRefErr, SelectorErr):
            bridge.put(out_q)
            continue

        try:
            id.clear()
            id.send_keys(bridge[0])

            name = wd2.find_element(By.XPATH, "//input[@id]='addBridgeName']")
            name.clear()
            name.send_keys(bridge[1])
            #~ bridge_name.send_keys(Keys.TAB, Keys.TAB, Keys.RETURN)

            btn = wd2.find_element(By.XPATH, ".//button[contains(text(), 'Save Changes')]").click()
        except (NotFoundErr, TimeoutErr, StaleRefErr, SelectorErr, InterceptErr):
            bridge.put(out_q)
            continue
        
        tries = 0

        time.sleep(0.1)


#~ opts = webdriver.FirefoxOptions()
#~ opts.add_argument('--headless')

wd1 = webdriver.Firefox()
wd2 = webdriver.Firefox()

while True:

    print('\nWhich account will be used?')

    opt = input('[1] man_team+SUT@een.com  OR  [2] man_team+SUT2@een.com?: ').lower()

    if opt == 1 or 'SUT':
        acct = 'man_team+SUT@een.com'
        break

    elif opt == 2 or 'SUT2':
        acct = 'man_team+SUT2@een.com'
        break

    print('\nGot invalid response:', str(opt), '\n')
    continue

in_q = queue.Queue()
out_q = queue.Queue()

t1 = threading.Thread(target=searcher, name='Thread 1', args=(in_q, out_q))
t1.daemon = True
t1.start()

t2 = threading.Thread(target=connecter, name='Thread 2', args=(out_q,))
t2.daemon = True
t2.start()

print('\nEnter or scan-in bridge serials continuously/as needed.')
print('This program will auto-search EEN Admin and attach the bridge in Viewer.')
print("If it fails to add the bridge in Viewer, then it will be re-added to queue.")
print('Tip: You can copy/paste multiple serials from Sheets and this should run each of them.\n')

while True:

    x = input('\n')

    if (x[0:6] == 'EEN-BR') and (len(x) >= 15):
        try:
            in_q.put(x)
        except queue.Full:
            continue
        else:
            print('\n' + x, 'added to queue.\n')
            continue
        
    print('\nSerial does not match proper format: EEN-BRXXX-XXXXXX\n')
    continue
