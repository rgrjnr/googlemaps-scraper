from datetime import datetime
from datetime import date
from firebase_admin import credentials, db, firestore, storage
from google.cloud.firestore_v1.base_query import FieldFilter, Or
from selenium import webdriver
from selenium.webdriver import Keys, ActionChains
from selenium.webdriver.common.by import By
import firebase_admin
import json
import get_token
import openai
import os
import urllib.request
import backoff
import uuid
from dotenv import load_dotenv
from slugify import slugify
import logging
from get_token import num_tokens_from_messages

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(
            f"logs/single-event-scraper-{datetime.today().strftime('%Y%m%d%H%M')}.log"
        ),
        logging.StreamHandler(),
    ],
)

driver = webdriver.Firefox(executable_path=r"/Users/rogerjunior/geckodriver")

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
cred = credentials.Certificate("firebase.json")
firebase_admin.initialize_app(cred, {"storageBucket": "the-queer-spot.appspot.com"})


with open("./reduce-page.js", "r") as f:
    js_code = "".join(f.readlines())

with open("./instructions/single-event.md", "r") as f:
    instructions = "".join(f.readlines())


@backoff.on_exception(
    backoff.constant, ValueError, interval=1, max_tries=2, max_time=60
)
def ask_openai(instruction, message):
    messages = [
        {
            "role": "system",
            "content": instruction,
        },
        {"role": "user", "content": message},
    ]

    request_tokens = num_tokens_from_messages(messages, model="gpt-3.5-turbo")

    if request_tokens > 4096:
        logging.warning("Token Limit exceeded")
        return

    logging.info(f"Asking ChatGPT - using {request_tokens} tokens.")

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        max_tokens=max(4096 - request_tokens, 256),
        messages=messages,
    )

    return response


def scrape_page(url):
    ## GET PAGE

    if "facebook.com" in url:
        url = "https://mbasic.facebook.com/events/" + url.split("/")[-2]
        print("Skipped \n\n\n")
        return None
    try:
        driver.get(url)

        # html = driver.execute_script(
        #     js_code.replace("|*SELECTOR*|", "body")
        # )

        html = driver.find_element(by=By.TAG_NAME, value="body")
        html = html.text

        if html == None:
            logging.error("No HTML found")
            return
    except:
        logging.error("Browser Error")
        return
    ## ASK CHATGPT
    try:
        response = ask_openai(
            instruction=instructions.format(datetime.today().strftime("%Y-%m-%d")),
            message=html,
        )
        logging.info("ChatGPT finished by: " + response.choices[0].finish_reason)

        # Tokens
        # tokens_used = response["usage"]["total_tokens"]
        # organizer_ref.update(
        #     {
        #         "tokens": firestore.Increment(tokens_used),
        #         "lastScrapeTime": datetime.today(),
        #     }
        # )

        # logging.info("Content: " + response.choices[0].message.content)

        try:
            res = json.loads(response.choices[0].message.content)
            return res
        except:
            logging.error("No valid response")
            return None
    except:
        logging.error("Error with ChatGPT")
        return


def update_event(event_data, event_id):
    db = firestore.client()
    event_ref = db.collection("events").document(event_id)

    event_ref.update(
        {
            "location": event_data["location"],
            "tickets": event_data["tickets"],
            "time": event_data["time"],
            "description": event_data["description"],
            "price": event_data["price"],
            "currency": event_data["currency"],
            "scraped": True,
        }
    )

    logging.info("Event Updated\n\n")


try:
    db = firestore.client()
    events = (
        db.collection("events")
        .where(filter=FieldFilter("date", ">=", datetime.today().strftime("%Y-%m-%d")))
        .stream()
    )

    for event in events:
        print(f"{event.id} => {event.to_dict()['eventURL']}")

        if event.to_dict().get("scraped"):
            print("already scraped \n\n")
            continue

        event_data = scrape_page(event.to_dict()["eventURL"])
        if event_data:
            update_event(event_data=event_data, event_id=event.id)

finally:
    driver.quit()
