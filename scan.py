#!/usr/bin/env python

from datetime import datetime
import struct
import select
import socket
import random
import json
import urllib2
import hashlib
import hmac
import base64

import trello
from twilio.rest import TwilioRestClient

import smtplib

from lib import trellodb
from lib import conf


def parse_scanner_data(scanner_data):
    upc_chars = []
    for i in range(0, len(scanner_data), 16):
        chunk = scanner_data[i:i+16]

        # The chunks we care about will match
        # __  __  __  __  __  __  __  __  01  00  __  00  00  00  00  00
        if chunk[8:10] != '\x01\x00' or chunk[11:] != '\x00\x00\x00\x00\x00':
            continue

        digit_int = struct.unpack('>h', chunk[9:11])[0]
        upc_chars.append(str((digit_int - 1) % 10))

    return ''.join(upc_chars)


class UPCAPI:
    BASEURL = 'https://www.digit-eyes.com/gtin/v2_0'

    def __init__(self, app_key, auth_key):
        self._app_key = app_key
        self._auth_key = auth_key

    def _signature(self, upc):
        h = hmac.new(self._auth_key, upc, hashlib.sha1)
        return base64.b64encode(h.digest())

    def _url(self, upc):
        return '{0}/?upcCode={1}&language=en&app_key={2}&signature={3}'.format(
            self.BASEURL, upc, self._app_key, self._signature(upc))

    def get_description(self, upc):
        """Returns the product description for the given UPC.
        
           `upc`: A string containing the UPC."""
        url = self._url(upc)
        print(("url :: {0}".format(url)))
        json_blob = urllib2.urlopen(url).read()
        #print "json_blob ::  \n {0}".format(str(json_blob))
        return json.loads(json_blob)['description']


def local_ip():
    """Returns the IP that the local host uses to talk to the Internet."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("trello.com", 80))
    addr = s.getsockname()[0]
    s.close()
    return addr


def generate_opp_id():
    return ''.join(random.sample('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789', 12))


def opp_url(opp):
    print("creating learning oppurtunity URL")
    print("opp :: " + str(opp) )
    return 'http://{0}/learn-barcode/{1}'.format(local_ip(), opp['opp_id'])


def create_barcode_opp(trello_db, barcode):
    """Creates a learning opportunity for the given barcode and writes it to Trello.
    
       Returns the dict."""
    print("create_barcode_opp")
    opp = {
        'type': 'barcode',
        'opp_id': generate_opp_id(),
        'barcode': barcode,
        'created_dt': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    print("opportunity :: {0}".format(opp))

    trello_db.insert('learning_opportunities', opp)
    return opp


def publish_barcode_opp(opp):
    print("publish barcode opportunity")
    message = '''Hi! Oliver here. You scanned a code I didn't recognize. Care to fill me in?  {0}'''.format(opp_url(opp))
    subject = '''Didn't Recognize Barcode'''
    communication_method = conf.get()['communication_method']
    if communication_method == 'email':
        print("sending email")
        send_via_email(message, subject)
    else:
        print("send phone message")
        send_via_twilio(message)

def send_via_twilio(msg):
    client = TwilioRestClient(conf.get()['twilio_sid'], conf.get()['twilio_token'])
    message = client.sms.messages.create(body=msg,
                                         to='+{0}'.format(conf.get()['twilio_dest']),
                                         from_='+{0}'.format(conf.get()['twilio_src']))

def send_via_email(msg, subject):
    to = conf.get()['email_dest']
    gmail_user = conf.get()['gmail_user'] 
    gmail_pwd = conf.get()['gmail_password']
    smtpserver = smtplib.SMTP("smtp.gmail.com",587)
    smtpserver.ehlo()
    smtpserver.starttls()
    smtpserver.ehlo
    smtpserver.login(gmail_user, gmail_pwd)
    header = 'To:' + to + '\n' + 'From: ' + gmail_user + '\n' + 'Subject: ' + subject + ' \n'
    print('\nSending email...\n')
    message = header + '\n ' + msg +' \n\n'
    smtpserver.sendmail(gmail_user, to, message)
    print('Email sent.')
    smtpserver.close()

def match_barcode_rule(trello_db, barcode):
    """Finds a barcode rule matching the given barcode.

       Returns the rule if it exists, otherwise returns None."""
    rules = trello_db.get_all('barcode_rules')
    for r in rules:
        if r['barcode'] == barcode:
            return r
    return None


def match_description_rule(trello_db, desc):
    """Finds a description rule matching the given product description.

       Returns the rule if it exists, otherwise returns None."""
    rules = trello_db.get_all('description_rules')
    for r in rules:
        print("checking against rule :: {0}".format(r))
        if r['search_term'].lower() in desc.lower():
            return r
    return None


def add_grocery_item(trello_api, item):
    """Adds the given item to the grocery list (if it's not already present)."""
    # Get the current grocery list
    print("add_grocery_item")
    grocery_board_id = conf.get()['trello_grocery_board']
    all_lists = trello_api.boards.get_list(grocery_board_id)
    grocery_list = [x for x in all_lists if x['name'] == conf.get()['trello_grocery_list']][0]
    cards = trello_api.lists.get_card(grocery_list['id'])
    card_names = [card['name'] for card in cards]

    # Add item if it's not there already
    if item not in card_names:
        print("Adding '{0}' to grocery list".format(item))
        trello_api.lists.new_card(grocery_list['id'], item)
    else:
        print("Item '{0}' is already on the grocery list; not adding".format(item))

print("Reading configuration file for data...")
trello_api = trello.TrelloApi(conf.get()['trello_app_key'])
trello_api.set_token(conf.get()['trello_token'])
trello_db = trellodb.TrelloDB(trello_api, conf.get()['trello_db_board'])

f = open(conf.get()['scanner_device'], 'rb')
while True:
    print('Waiting for scanner data')

    # Wait for binary data from the scanner and then read it
    scan_complete = False
    scanner_data = ''
    while True:
        rlist, _wlist, _elist = select.select([f], [], [], 0.1)
        if rlist != []:
            new_data = ''
            while not new_data.endswith('\x01\x00\x1c\x00\x01\x00\x00\x00'):
                new_data = rlist[0].read(16)
                scanner_data += new_data
            # There are 4 more keystrokes sent after the one we matched against,
            # so we flush out that buffer before proceeding:
            [rlist[0].read(16) for i in range(4)]
            scan_complete = True
        if scan_complete:
            break
 
    # Parse the binary data as a barcode
    barcode = parse_scanner_data(scanner_data)
    print("Scanned barcode '{0}'".format(str(barcode)))

    # Match against barcode rules
    try:        
        barcode_rule = match_barcode_rule(trello_db, barcode)
        print("Barcode Rule :: {0}".format(str(barcode_rule)))
        if barcode_rule is not None:
            print("Adding grocery item")
            add_grocery_item(trello_api, barcode_rule['item'])
            continue
    except requests.exceptions.HTTPError as e:
        print("HttpError occurred :: {0}".format(e.msg))
        continue

    # Get the item's description
    u = UPCAPI(conf.get()['digiteyes_app_key'], conf.get()['digiteyes_auth_key'])
    try:
        print("Attempting to fetch a description...")
        desc = u.get_description(barcode)
        print("Received description '{0}' for barcode {1}".format(desc, repr(barcode)))
    except urllib2.HTTPError, e:
        if 'UPC/EAN code invalid' in e.msg:
            print("Barcode {0} not recognized as a UPC; creating learning opportunity".format(repr(barcode)))
            opp = create_barcode_opp(trello_db, barcode)
            print("Publishing learning opportunity")
            publish_barcode_opp(opp)
            continue
        elif 'Not found' in e.msg:
            print("Barcode {0} not found in UPC database; creating learning opportunity".format(repr(barcode)))
            opp = create_barcode_opp(trello_db, barcode)
            print("Publishing learning opportunity via SMS")
            publish_barcode_opp(opp)
            continue
        else:
            print("RAISING ERROR :: ")
            print(str(e.msg))
            raise
    except ValueError as ve:
        print("Caught Value Error :: ")
        desc = ''
        continue        ## TODO Fix this stuff here

    # Match against description rules
    desc_rule = match_description_rule(trello_db, desc)
    if desc_rule is not None:
        add_grocery_item(trello_api, desc_rule['item'])
        continue

    print("Don't know what to add for product description '{0}'".format(desc))
    print("lets try adding a learning opportunity for barcode : {0}".format(barcode))
    opp = create_barcode_opp(trello_db, barcode)
    print("our oppurtunity :: {0} ".format(opp))
    publish_barcode_opp(opp)
    continue

