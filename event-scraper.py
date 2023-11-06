from datetime import datetime
from datetime import date
from firebase_admin import credentials, db, firestore, storage
from google.cloud.firestore_v1.base_query import FieldFilter, Or
from selenium import webdriver
from selenium.webdriver import Keys, ActionChains
from selenium.webdriver.common.by import By
import firebase_admin
import json
import openai
import os
import urllib.request
import uuid
import tiktoken
from dotenv import load_dotenv
from slugify import slugify
import logging
from get_token import num_tokens_from_messages

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(
            f"logs/event-scraper-{datetime.today().strftime('%Y%m%d%H%M')}.log"
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


def event_exists(event):
    ## CHECK IF EXISTS AND SKIP
    if event["date"]:
        db = firestore.client()

        event_results = (
            db.collection("events")
            .where(filter=FieldFilter("name", "==", event["name"]))
            .stream()
        )

        for doc in event_results:
            if event["date"] == doc.to_dict()["date"]:
                logging.warning("⏭️ " + event["name"] + " already exists. Skiped.")
                return True


def find_venue(event, organizer):
    db = firestore.client()
    found_venue = False

    if event["location"] == None:
        return None

    venues_results = (
        db.collection("venues")
        .where(
            filter=FieldFilter(
                "alternativeNames", "array_contains", event["location"].lower()
            )
        )
        .stream()
    )

    for doc in venues_results:
        found_venue = True
        logging.info("Venue: Found")
        return db.collection("venues").document(doc.id)

    if found_venue == False:
        if "fallbackVenue" in organizer:
            logging.info("Venue: Fallback")
            return organizer.get("fallbackVenue")
        else:
            logging.info("Venue: None")
            return None


def scrape_page(organizer_ref, events=False, force_scrape=False):
    organizer = organizer_ref.get().to_dict()
    organizer["fallbackCurrency"] = organizer.get("fallbackCurrency", "EUR")

    ## GET PAGE
    driver.get(organizer["crawlerURL"])
    html = driver.execute_script(
        js_code.replace("|*SELECTOR*|", organizer.get("selector", "body"))
    )

    print(html)

    if (
        "lastCrawlHTML" in organizer and html == organizer["lastCrawlHTML"]
    ) and force_scrape == False:
        logging.info("HTML didn't change")
        return
    else:
        logging.info("HTML changed, continue process..")
        organizer_ref.update({"lastCrawlHTML": html})

    if html == None:
        logging.error("No HTML found")
        return

    ## ASK CHATGPT
    try:
        if events == False:
            messages = [
                {
                    "role": "system",
                    "content": f"You will be provided with an HTML source code. Your job is to extract all events listed and then format them like a JSON array of objects. Your response should contain only the resulting JSON with the following keys and formats:\n- 'price' - look for '€', 'R$' or '$'. Format as a number like this 9.99. This should be a JSON number, which means no letters or apostrophes.\n- 'currency' - should be 'EUR', 'BRL' or 'USD'\n- 'name',\n- 'date' - in the pattern: YYYY-MM-DD. Note that today is {datetime.today().strftime('%Y-%m-%d')} so format dates written as weekdays accordingly.\n-'time' - in the pattern: HH:MM\n- 'image',\n- 'eventURL',\n- 'location' as a string only",
                },
                {"role": "user", "content": html},
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

            logging.info("ChatGPT finished by: " + response.choices[0].finish_reason)

            # Tokens
            tokens_used = response["usage"]["total_tokens"]
            organizer_ref.update(
                {
                    "tokens": firestore.Increment(tokens_used),
                    "lastScrapeTime": datetime.today(),
                }
            )

            ##logging.info("Content: " + response.choices[0].message.content)
            try:
                events = json.loads(response.choices[0].message.content)
                print(events)
            except:
                logging.error("No valid response")
                return

        else:
            logging.warning("Skipping ChatGPT")
    except:
        logging.error("Error with ChatGPT")
        return

    ## UPLOAD FOUND EVENTS TO DB
    db = firestore.client()
    bucket = storage.bucket()

    logging.info("\n[" + str(len(events)) + "] events found in last scrape:")

    for event in events:
        if event_exists(event):
            continue

        ########### CREATE
        event["createdAt"] = firestore.SERVER_TIMESTAMP
        event["organizer"] = organizer_ref

        # Upload image
        try:
            if event["image"]:
                url = event["image"]
                extension = urllib.request.urlopen(url).info().get_content_subtype()
                local_image = f"events/{str(uuid.uuid4())}.{extension}"
                urllib.request.urlretrieve(url, local_image)
                blob = bucket.blob(local_image)
                blob.upload_from_filename(local_image)
                blob.make_public()
                event["image"] = blob.public_url
        except:
            logging.info("Error downloading image. Skipping this.")

        # Event URL
        if event["eventURL"]:
            event["eventURL"] = (
                organizer.get("fallbackStartURL", "") + event["eventURL"]
            )

        # Fallbacks
        organizer["fallbackCurrency"] = (
            organizer["fallbackCurrency"] if organizer["fallbackCurrency"] else "EUR"
        )

        event["currency"] = (
            event["currency"] if event["currency"] else organizer["fallbackCurrency"]
        )

        # Price
        event["price"] = None if event["price"] == "" else event["price"]

        # Find venues
        event["venue"] = find_venue(event, organizer)

        event_ref = db.collection("events").document(
            slugify(
                event["name"]
                + "-"
                + slugify(organizer["name"])
                + "-"
                + str(event["date"])
            )
        )

        if event["date"] == None:
            event["public"] = False
            event["needsReview"] = True

        event["organizerData"] = organizer
        event_ref.set(event)

        event["scraped"] = False

        logging.info("✅ " + event["name"] + " was created succesfully")


def run_organizer(id):
    db = firestore.client()
    organizer = db.collection("organizers").document(id)
    scrape_page(
        organizer
    )  # , force_scrape=True)  # , events=json.loads(chatgptresponse))


def run_organizers():
    db = firestore.client()
    organizers = db.collection("organizers").get()

    logging.info(str(len(organizers)) + " organizers found.")

    for organizer in organizers:
        logging.info("\n\n" + organizer.to_dict()["name"] + " ============")
        run_organizer(organizer.id)


try:
    run_organizers()
finally:
    driver.quit()
