import requests
import csv
import json
from utils import get_proxy

class TooManyCards(Exception):
    pass

class ErrorGettingCards(Exception):
    pass

class ErrorLoggingIn(Exception):
    pass

class Card:
    def __init__(self, idno, name, number, month, year, cvv, unused):
        self.id = idno
        self.name = name
        self.number = number
        self.month = month
        self.year = year
        self.unused = unused
        self.cvv = cvv

    def __repr__(self):
        return f"ID: {self.id} -- Name: {self.name} -- Number: {self.number} -- Exp: {self.month}/{self.year} -- Latest Transaction: {self.latest_transaction}"

class App:
    def __init__(self, proxy = None):
        self.token = ""
        self.sessionID = ""
        self.session = requests.session()
        self.proxy = proxy
        self.cardsJSON = None
        self.transactionsJSON = None
        self.tfa = False
        self.cards = []
        self.headers = {
            'Connection': 'keep-alive',
            'Accept': 'application/json, text/plain, */*',
            'Sec-Fetch-Dest': 'empty',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36',
            'Content-Type': 'application/json;charset=UTF-8',
            'Origin': 'https://privacy.com',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Referer': 'https://privacy.com/login',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        try:
            with open("cards.json", "r") as cardDBfile:
                self.createdCardsList = json.loads(cardDBfile.read())
        except FileNotFoundError:
            self.createdCardsList = []

    
    def closeSession(self):
        self.session.close()


    def login(self):
        email = input("Please input email: ")
        password = input("Please enter password: ")

        # Sometimes I get timeouts if I try to log in too many times in a row
        print("Trying to log in, this may take a while. ")
        r = self.session.get("https://privacy.com/", proxies=self.proxy)
        print(r)
        sessionID = self.session.cookies.get_dict()["sessionID"]
        self.sessionID = sessionID

        self.headers['Referer'] = 'https://privacy.com/login'

        data_obj = {"email": f"{email}", "password": f"{password}",
                    "extensionInstalled": "false"}

        data = json.dumps(data_obj)

        response = self.session.post(
            'https://privacy.com/auth/local', headers=self.headers, data=data, proxies=self.proxy)
        
        if response.status_code != 200:
            print(f"login response: {response} -- exiting. Try with a proxy!")
            raise ErrorLoggingIn
        
        try:
            token = response.json()["token"]
        except KeyError:
            # If the json doesnt have a ["token"] field then we got some oddball message. Probably 2FA
            print(response.json()["message"])
            if(response.json()["oneTimeCode"]):
                self.tfa = True
                code = (input("Please enter your 2fa code"))
                token = response.json()["userToken"]
                data_obj = {"code": code, "userToken": token, "rememberDevice": True}
                self.headers["Referer"] = "https://privacy.com/tfa"
                response = self.session.post('https://privacy.com/auth/local/code', headers=self.headers, data=json.dumps(data_obj), proxies=self.proxy)
                token = response.json()["token"]
            else:
                #If its not 2FA then something else went wrong
                raise ErrorLoggingIn

        #if for somereason we got a 200 response code but no json, then we fucked up somehow
        except json.decoder.JSONDecodeError:
            print("JSON Decode Error")
            print(response.text)
            raise ErrorLoggingIn
        print(f"logged in: {response}")
        self.token = token
        print("Getting Card Info... ")

        try:
            self.list_cards()
        except ErrorGettingCards as e:
            raise e

    def list_cards(self):
        #if we ran into 2FA then we need to change the referer
        if self.tfa:
            self.headers["Referer"] = "https://privacy.com/tfa"
            self.headers["Authorization"] = "Bearer " + self.token
        else: 
            self.headers["Authorization"] = "Bearer " + self.token
        r = self.session.get("https://privacy.com/api/v1/card", headers=self.headers, proxies=self.proxy)
        self.cardsJSON = r.json()

        #this try/catch may be redundant but I kept it just in case
        try:
            for card in self.cardsJSON["cardList"]:
                if card["state"] == "OPEN":
                    self.cards.append(Card(str(card["cardID"]), card["memo"], card["PAN"], card["expMonth"], card["expYear"], card["CVV"], card["unused"]))
        except KeyError:
            print(r.text)
            raise ErrorGettingCards
        r = self.session.get(
            "https://privacy.com/api/v1/transaction", headers=self.headers, proxies=self.proxy)
        self.transactionsJSON = r.json()

        #same as above try/catch.
        try:
            for card in self.cards:
                for transaction in self.transactionsJSON["transactionList"]:
                    if card.id == str(transaction["cardID"]):
                        card.latest_transaction = transaction["descriptor"]
                        break
                    else:
                        card.latest_transaction = ""
        except KeyError:
            print(r.text)
            raise ErrorGettingCards


    def deleteCard(self, cardID):
        self.headers['Authorization'] = "Bearer " + self.token
        self.headers["Referer"] = "https://privacy.com/home"
        response = self.session.post(f'https://privacy.com/api/v1/card/{cardID}/close', headers=self.headers, proxies=self.proxy)
        print(response.text)

    def run(self):
        try:
            self.login()
        except (ErrorGettingCards, ErrorLoggingIn) as e:
            raise(e)
        print(self.session.cookies.get_dict())
        choice = input("1 to list cards, 2 to create, 3 to export to CSV (AYCD Compatible), 4 to delete specific cards, 5 to delete all used cards ")
        if choice == "1":

            # with open('export.csv', 'w', newline='') as file:
            #     writer = csv.writer(file)
            #     for card in self.cards:
            #         writer.writerow([card["name"], card["number"], card["month"],
            #                          card["year"], card["cvv"], card["unused"], card["latest_transaction"]])
            for card in self.cards:
                print(card)
            return
        if choice == "2":

            self.headers['Authorization'] = "Bearer " + self.token
            self.headers['Referer'] = 'https://privacy.com/cards'
            print("Press CTRL C to exit... ")
            try:
                while True:
                    name = input("name your card: ")
                    data_obj = {"type": "MERCHANT_LOCKED"}
                    data_obj["memo"] = name
                    data = json.dumps(data_obj)

                    response = self.session.post(
                        'https://privacy.com/api/v1/card', headers=self.headers, data=data, proxies = self.proxy)
                    r_json = response.json()
                    try:
                        # If we get a message with this request, we probably made too many cards. Print the message to be safe, and raise an error.
                        if r_json['message']:
                            print(r_json['message'])
                            raise TooManyCards
                    except KeyError:
                        # We didnt get any message so we should continue
                        pass
            except (KeyboardInterrupt):
                print("Keyboard interrupt used. Returning")
                return
            except TooManyCards:
                print("You've made too many cards recently. You can't make anymore.")
                return


        if choice == "3":
            with open("config.json", "r") as config:
                json_text = config.read()
                configObj = json.loads(json_text)
            profile = configObj["profiles"]["Main"][0]
            with open("Export.csv", "w") as csv:
                csv.write("Email Address,Profile Name,Only One Checkout,Name on Card,Card Type,Card Number,Expiration Month,Expiration Year,CVV,Same Billing/Shipping,Shipping Name,Shipping Phone,Shipping Address,Shipping Address 2,Shipping Address 3,Shipping Post Code,Shipping City,Shipping State,Shipping Country,Billing Name,Billing Phone,Billing Address,Billing Address 2,Billing Address 3,Billing Post Code,Billing City,Billing State,Billing Country,otherEntriesList\n")
                for card in self.cards:
                    csv.write(f'{profile["email"]},{card.name},false,{profile["first"]} {profile["last"]},Visa,{card.number},{card.month},{card.year},{card.cvv},false,{profile["first"]} {profile["last"]},{profile["telephone"]},{profile["address"]},{profile["address2"]},,{profile["zip"]},{profile["city"]},{profile["state"]},United States,{profile["first"]} {profile["last"]},{profile["telephone"]},{profile["address"]},{profile["address2"]},,{profile["zip"]},{profile["city"]},{profile["state"]},United States,[]\n')

        if choice == "4":
            print("Press CTRL C to exit... ")
            try:
                while(True):
                    print("Pick a card to delete: ")
                    for card in self.cards:
                        print(card)
                    validID = 0
                    idno = input("Type the id number of the card ")
                    while not validID:
                        idno = input("Type the id number of the card ")
                        for card in self.cards:
                            print(card.id)
                            if idno == card.id:
                                validID = 1
                        if not validID:
                            print("Invalid ID")
                    self.deleteCard(idno)
                    self.list_cards()
            except KeyboardInterrupt:
                print("Keyboard interrupt used. Returning ")
                return
        
        if choice == "5":
            try:
                input("WARNING THIS WILL DELETE ALL CARDS... PRESS ENTER TO CONTINUE OR CTRL+C TO EXIT")
                input("PLEASE CONFIRM YOUR CHOICE... PRESS ENTER TO CONTINUE OR CTRL+C TO EXIT")
                for card in self.cards:
                    if not card.unused:
                        print(f"Deleting card {card.name}")
                        self.deleteCard(card.id)
                        print(f"Deleted card {card.name}")
                self.list_cards()
            except KeyboardInterrupt:
                return


if __name__ == "__main__":
    
    use_proxy = int(input("Would you like to use a proxy?, (1) YES, (0) NO"))
    if use_proxy:
        app = App(get_proxy())
    else:
        app = App()
    try:
        app.run()
    except:
        app.closeSession()
    app.closeSession()
