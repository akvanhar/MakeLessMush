# Utility file to seed ratings database from MovieLens data in seed_data

from model import (connect_to_db, User,
                   Friendship, Food, Message,
                   Allergen, Location)
from server import app
from datetime import datetime


def load_users():
    # Load users from sampleusers into database.

    user_file = open('sampledata/sampleusers.txt')

    for line in user_file:
        email, password, fname, lname, fb_id = line.split("|")
        fb_id = int(fb_id)
        if password == "":
            password = None
        User.add_user(email, fname, lname, password, fb_id)


def load_listings():
    # Load listings from samplelistings into database

    listings_file = open('sampledata/samplelistings.txt')

    for line in listings_file:
        (title,
         texture,
         datemade,
         quantity,
         freshfrozen,
         description,
         allergen_list,
         user_id,
         phone_number,
         lat,
         lng) = line.split("|")
        allergen = Allergen.add_allergen(allergen_list)
        location = Location.add_location(lat, lng)
        Food.add_food(title,
                      texture,
                      datemade,
                      quantity,
                      freshfrozen,
                      description,
                      allergen.allergen_id,
                      user_id,
                      location.location_id,
                      phone_number)

def load_messages():
    # Load messages from samplemessages into database

    messages_file = open('sampledata/samplemessages.txt')

    for line in messages_file:
        line = line.rstrip()
        sender_id, receiver_id, message_sent = line.split("|")
        Message.add_message(sender_id, receiver_id, message_sent)

if __name__ == "__main__":
    connect_to_db(app)

    # load_users()
    # load_listings()
    load_messages()
