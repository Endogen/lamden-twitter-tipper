#!/usr/bin/env python3

CONSUMER_KEY = "<some key>"
CONSUMER_SEC = "<some secret>"
ACCESS_TKN_KEY = "<some access token key>"
ACCESS_TKN_SEC = "<some access token secret>"

AMOUNT_TAU = 10
BOT_PRIVKEY = "<some Lamden private key>"

TESTNET_URL = "https://testnet-master-1.lamden.io"
MAINNET_URL = "https://masternode-01.lamden.io"
LAMDEN_URL = TESTNET_URL

import requests
import logging
import tweepy
import time
import json
import os

from tweepy import Stream, StreamListener
from lamden.crypto.transaction import build_transaction
from lamden.crypto.wallet import Wallet

USER_FILE = "users.txt"

user_list = list()
bot_wallet = Wallet(BOT_PRIVKEY)


def is_address_valid(address: str):
    """ Check if the given address is valid """
    if not len(address) == 64:
        return False
    try:
        int(address, 16)
    except:
        return False
    return True


def add_user(user: str):
    user_list.append(str(user))

    try:
        file = open(USER_FILE, 'a')
    except FileNotFoundError:
        file = open(USER_FILE, 'w')

    file.write(f"{user}\n")
    file.close()


def tip(address: str):
    nonce = requests.get(f"{LAMDEN_URL}/nonce/{bot_wallet.verifying_key}")
    nonce = json.loads(nonce.text)

    # Build transaction
    tx_data = build_transaction(
        wallet=bot_wallet,
        processor=nonce["processor"],
        stamps=100,
        nonce=nonce["nonce"],
        contract="currency",
        function="transfer",
        kwargs={"amount": AMOUNT_TAU, "to": address}
    )

    # Send transaction
    tx = requests.post(LAMDEN_URL, data=tx_data)
    logging.debug(f"Sent {AMOUNT_TAU} TAU to {address} - {tx.text}")


class HandleListener(StreamListener):

    def __init__(self, twitter_api):
        super().__init__(twitter_api)
        self.api = twitter_api

    def on_data(self, data):
        logging.debug(f"New mention - {data}")

        name = f"@{self.api.me().name}"

        data = json.loads(data)
        user = data["user"]["id"]
        if str(user) not in user_list:
            text = data["text"]
            text = text.replace(name, "")

            for t in text.split():
                if is_address_valid(t):
                    add_user(user)
                    tip(t)
                    break
                else:
                    logging.debug(f"Not a valid address: {t}")
        else:
            msg = f"User already in list"
            logging.debug(msg)
        return True

    def on_error(self, status):
        logging.error(status)


def create_kill_script(filename):
    shebang = "#!/bin/bash"
    command = f"kill -9 {os.getpid()}"

    with open(filename, "w") as f:
        f.truncate(0)
        f.write(f"{shebang}\n\n{command}")


if __name__ == '__main__':
    # Create script to kill bot by PID
    create_kill_script("kill.sh")

    if os.path.isfile(USER_FILE):
        with open(USER_FILE, "r") as f:
            user_list = f.read().splitlines()

    # Set credentials for Twitter access
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SEC)
    auth.set_access_token(ACCESS_TKN_KEY, ACCESS_TKN_SEC)

    # Authenticate
    api = tweepy.API(auth)

    stream = Stream(auth, HandleListener(api))
    stream.filter(track=[f"@{api.me().screen_name}"])

    while True:
        time.sleep(0.01)
