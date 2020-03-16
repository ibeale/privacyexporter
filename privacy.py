import requests
import csv
import json


class App:
    def __init__(self):
        self.token = ""
        self.sessionID = ""
        self.session = None
        self.cardsJSON = None
        self.transactionsJSON = None
        self.cards = []

    def login(self):
        email = input("Please input email: ")
        password = input("Please enter password: ")
        print("Trying to log in")
        self.session = requests.session()
        r = self.session.get("https://privacy.com/")
        print(r)
        sessionID = self.session.cookies.get_dict()["sessionID"]
        self.sessionID = sessionID
        print("logged in")

        headers = {
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

        data_obj = {"email": f"{email}", "password": f"{password}",
                    "extensionInstalled": "false"}

        data = json.dumps(data_obj)

        response = self.session.post(
            'https://privacy.com/auth/local', headers=headers, data=data)
        print(response)
        token = response.json()["token"]
        self.token = token

    def list_cards(self):
        headers = {"Authorization": "Bearer " + self.token}
        r = requests.get("https://privacy.com/api/v1/card", headers=headers)
        self.cardsJSON = r.json()

    def list_transactions(self):
        headers = {"Authorization": "Bearer " + self.token}
        r = requests.get(
            "https://privacy.com/api/v1/transaction", headers=headers)
        self.transactionsJSON = r.json()

    def run(self):
        self.login()
        print(self.session.cookies.get_dict())
        choice = input("1 to export all to csv, 2 to create")
        if choice == "1":
            self.list_cards()
            for card in self.cardsJSON["cardList"]:
                if card["state"] == "OPEN":
                    self.cards.append({
                        "id": str(card["cardID"]),
                        "name": card["memo"],
                        "number": card["PAN"],
                        "month": card["expMonth"],
                        "year": card["expYear"],
                        "cvv": card["CVV"],
                        "unused": card["unused"],
                        "limit": "$"+str(card["spendLimit"])+" per "+card["spendLimitDuration"]
                    })

            self.list_transactions()

            for card in self.cards:
                for transaction in self.transactionsJSON["transactionList"]:
                    if card["id"] == str(transaction["cardID"]):
                        card["latest_transaction"] = transaction["descriptor"]
                        break
                    else:
                        card["latest_transaction"] = ""

            with open('export.csv', 'w', newline='') as file:
                writer = csv.writer(file)
                for card in self.cards:
                    writer.writerow([card["name"], card["number"], card["month"],
                                     card["year"], card["cvv"], card["unused"], card["latest_transaction"]])
        if choice == "2":
            name = input("name your card: ")

            headers = {
                'Connection': 'keep-alive',
                'Accept': 'application/json, text/plain, */*',
                'Sec-Fetch-Dest': 'empty',
                'Authorization': "Bearer " + self.token,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36',
                'Content-Type': 'application/json;charset=UTF-8',
                'Origin': 'https://privacy.com',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-Mode': 'cors',
                'Referer': 'https://privacy.com/cards',
                'Accept-Language': 'en-US,en;q=0.9',
            }

            data_obj = {"type": "MERCHANT_LOCKED"}
            data_obj["memo"] = name
            data = json.dumps(data_obj)

            response = self.session.post(
                'https://privacy.com/api/v1/card', headers=headers, data=data)
            print(response.json())


if __name__ == "__main__":
    app = App()
    app.run()
