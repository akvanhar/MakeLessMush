"""Make Less Mush"""
import os
import json

from jinja2 import StrictUndefined

from flask import (Flask, render_template, redirect,
                   request, flash, session, jsonify)
from flask_debugtoolbar import DebugToolbarExtension

from datetime import datetime

from sqlalchemy import desc

from model import (db, connect_to_db, User,
                   Friendship, Food, Message,
                   Allergen, Location)

from titlecase import titlecase

from twilio_send_sms import send_text

from helper import get_user, get_new_messages, check_login, get_messages

app = Flask(__name__)

google_api = os.environ['GOOGLE_MAPS_API_KEY']

app.config['SECRET_KEY'] = os.environ['FLASK_SECRET_KEY']

# Set this in order to raise Jinja errors.
app.jinja_env.undefined = StrictUndefined


@app.route('/')
def spalsh():
    # splash page for Make Less Mush

    return render_template('splash.html')


@app.route('/home')
def home():
    # homepage

    if check_login('Please login.') == 'not_logged_in':
        return redirect('/login')

    else:
        user = get_user()
        new_messages = get_new_messages(session['user_id'])
        user_friends = user.friendships

        if user_friends:
            # get this user's friend ids
            friend_ids = [friend.friend_id for friend in user_friends]
            friends_fb_ids = db.session.query(User.user_id,
                                              User.fb_id).filter(
                                              User.user_id.in_(friend_ids)
                                              ).all()

            # get all their friend's listings
            friends_listings = []
            for friend in friend_ids:
                listing = Food.query.filter_by(active=True
                                               ).filter(
                                               Food.user_id == friend
                                               ).order_by(desc('post_date')
                                                          ).first()
                if listing:
                    friends_listings.append(listing)

            # get the food ids so they can be filtered out
            friends_food_ids = [food.food_id for food in friends_listings]

            user_id = session['user_id']

            # get all the other active listings,
            # leaving out friend and user listings
            other_listings = Food.query.filter_by(active=True
                                                  ).filter(
                                                  (~Food.user_id.in_(friend_ids)),
                                                  (~(Food.user_id == user_id))
                                                  ).order_by(desc('post_date')
                                                             ).all()

            # combine listings so that the friends listings come first
            this_users_listings = friends_listings + other_listings
            short_list = this_users_listings[:5]
        else:
            short_list = Food.query.filter_by(active=True
                                              ).order_by(desc('post_date')
                                                         ).limit(5).all()
            friends_fb_ids = None

        current_date = datetime.now()
        current_date = current_date.strftime("%Y-%m-%d")

        return render_template('index.html',
                               user_listings=short_list,
                               current_date=current_date,
                               user=user,
                               new_messages=new_messages,
                               user_friends=user_friends,
                               friends_fb_ids=friends_fb_ids)


@app.route('/login')
def login():
    # Login page.

    return render_template("login.html")


@app.route('/login_portal', methods=['POST'])
def login_portal():
    # Handles the login form

    email = request.form.get('email')
    password = request.form.get('password')
    password = hash(password)
    user = User.query.filter_by(email=email, password=password).first()

    if user:
        session['user_id'] = user.user_id
        flash('Login successful!')
        return redirect('/home')
    else:
        flash('Login unsuccessful. Please try again')
        return redirect('/login')


@app.route('/facebook_login_portal', methods=['POST'])
def facebook_login():
    # Handles the login from the facebook login button

    fb_user_id = request.form.get('fbUserId')
    fb_fname = request.form.get('fbFname')
    fb_lname = request.form.get('fbLname')
    fb_email = request.form.get('fbEmail')
    current_acces_token = request.form.get('accessToken')
    fb_friends = request.form.get('fbFriends')

    fb_friends = json.loads(fb_friends)
    fb_user = User.query.filter_by(fb_id=fb_user_id).first()

    if fb_user:
        # User has previously logged into MLM
        user_id = fb_user.user_id
        session['user_id'] = user_id
        session['current_acces_token'] = current_acces_token

        # check friends list in friends table. If friendship not there, add it.
        if fb_friends:
            friends_user_ids = []
            # turn the fb_ids into user_ids.
            for friend_fb_id in fb_friends:
                friend_user_id = db.session.query(User.user_id
                                                  ).filter_by(
                                                  fb_id=friend_fb_id
                                                  ).first()
                friends_user_ids.append(friend_user_id)
            friends_user_ids = [x[0] for x in friends_user_ids]

            # now see if those friends are in the friendship table.
            for friend in friends_user_ids:
                friend_exists = db.session.query(Friendship.friend_id
                                                 ).filter_by(friend_id=friend
                                                             ).first()
                # if they're not, add them in! Yay friendship!
                if friend_exists is None:
                    Friendship.add_friendship(user_id, friend)

        flash('Login successful!')

        return redirect('/home')
    else:
        # First time for user logging into MLM
        # add the user to the database
        User.add_user(email=fb_email, fname=fb_fname,
                      lname=fb_lname, fb_id=fb_user_id)
        # access that user's information, add it to the session
        fb_user = User.query.filter_by(fb_id=fb_user_id).first()
        user_id = fb_user.user_id

        session['user_id'] = user_id
        session['current_acces_token'] = current_acces_token

        flash('Thanks for creating an account with Make Less Mush')

        return redirect('/home')


@app.route('/logbutton')
def logbutton():
    # You get here if you click the login/logout button from any page
    # other than login/signup

    if 'user_id' in session:
        del session['user_id']
        flash("Logout successful!")
    if 'current_acces_token' in session:
        del session['current_acces_token']
        flash("You have logged out of Facebook")

    return redirect("/login")


@app.route('/signup')
def signup():
    # Allows a user to signup for Make Less Mush

    return render_template('signup.html')


@app.route('/signup_portal', methods=['POST'])
def signup_portal():
    # Handles the signup form

    email = request.form.get('email')
    password = request.form.get('password')
    password = hash(password)
    fname = request.form.get('fname')
    fname = titlecase(fname)
    lname = request.form.get('lname')
    lname = titlecase(lname)
    User.add_user(email, fname, lname, password)

    # automatically sign in user after account creation
    user = User.query.filter_by(email=email, password=password).first()
    user_id = user.user_id
    session['user_id'] = user_id
    flash('Account successfully created. Welcome to Make Less Mush!')

    return redirect('/home')


@app.route('/fblogout_portal')
def logout_portal():
    # Handles logout of MLM
    # FIXTHIS

    return redirect('/login')


@app.route('/postlisting', methods=['POST'])
def postlisting():
    # Handles a new listing being submitted

    title = request.form.get('title')
    title = titlecase(title)
    texture = request.form.get('texture')
    datemade = request.form.get('datemade')
    quantity = request.form.get('quantity')
    freshfrozen = request.form.get('freshfrozen')
    description = request.form.get('description')
    allergens = request.form.getlist('allergens')
    user_id = session['user_id']
    phone_number = request.form.get('phone_number')
    geoCheckbox = request.form.get('geoCheckbox')

    if len(phone_number) == 17:
        phone_number = phone_number[4:7]+phone_number[9:12]+phone_number[13:]
    else:
        phone_number = None

    allergen = Allergen.add_allergen(allergens)
    allergen_id = allergen.allergen_id

    if geoCheckbox:
        lat = request.form.get('lat')
        lng = request.form.get('lng')
        location = Location.add_location(lat, lng)
        location_id = location.location_id
    else:
        location_id = None

    Food.add_food(title, texture, datemade, quantity, freshfrozen,
                  description, allergen_id, user_id, location_id,
                  phone_number)

    flash('Your mush has been successfully posted!')

    return redirect('/home')


@app.route('/listings.json')
def display_listings():
    # Query database for posts active listings.
    # Return listings as a JSON object.
    # FIXTHIS: return onlly active listings
    location_results = Location.query.all()

    if not location_results:
        # FIXTHIS: return an error message
        pass
    else:
        locations = {}

        for location in location_results:
            locations[location.location_id] = {
                "title": (location.foods[0]).title,
                "date_posted": (location.foods[0]
                                ).post_date.strftime("%Y-%m-%d"),
                "posting_user": (location.foods[0]).user.fname,
                "posting_user_id": (location.foods[0]).user_id,
                "food_id": (location.foods[0]).food_id,
                "latitude": location.latitude,
                "longitude": location.longitude
            }

    return jsonify(locations)


@app.route('/listings')
def listings():
    # Lists all the food listings, putting the user's friends'
    # listings first.

    if check_login('Please login to view listings.') == 'not_logged_in':
        return redirect('/login')

    else:
        user = get_user()
        new_messages = get_new_messages(session['user_id'])
        user_friends = user.friendships

        if user_friends:
            friend_ids = [friend.friend_id for friend in user_friends]

            # get all their friend's listings
            friends_listings = Food.query.filter_by(active=True
                                                    ).filter(
                                                    Food.user_id.in_(friend_ids)
                                                    ).order_by(
                                                    desc('post_date')
                                                    ).all()

            # get the food ids so they can be filtered out
            friends_food_ids = [food.food_id for food in friends_listings]

            # get all the other active listings
            other_listings = Food.query.filter_by(active=True
                                                  ).filter(~Food.food_id.in_(
                                                   friends_food_ids)
                                                   ).order_by(desc('post_date')
                                                              ).all()

            # combine listings so that the friends listings come first
            foods = friends_listings + other_listings

        else:
            foods = Food.query.filter_by(active=True).order_by(desc
                                                               ('post_date')
                                                               ).all()

        API_KEY = google_api

        return render_template('listings.html',
                               foods=foods,
                               user=user,
                               new_messages=new_messages,
                               API_KEY=API_KEY)


@app.route('/listings/<int:food_id>')
def food_info(food_id):
    # Display information about a specific food listing.

    if check_login('Please login to view listing details.') == 'not_logged_in':
        return redirect('/login')
    else:
        # get specific listing from db.
        food_listing = Food.query.get(food_id)
        user = get_user()
        new_messages = get_new_messages(session['user_id'])

        return render_template('food_info.html',
                               food_listing=food_listing,
                               user=user,
                               new_messages=new_messages)


@app.route('/mylistings')
def user_listings():
    # Shows a list of all of that particular user's listings.

    if check_login('Please login to view your listings.') == 'not_logged_in':
        return redirect('/login')
    else:
        # show user's listings.
        user = get_user()
        new_messages = get_new_messages(session['user_id'])
        user_id = session['user_id']
        question = Food.query
        user_listings = question.filter(Food.user_id == user_id,
                                        Food.active == True
                                        ).order_by(desc('post_date')).all()
        old_listings = question.filter(Food.user_id == user_id,
                                       Food.active == False
                                       ).order_by(desc('post_date')).all()

        return render_template('mylistings.html',
                               user_listings=user_listings,
                               old_listings=old_listings,
                               user=user,
                               new_messages=new_messages)


@app.route('/listings/edit/<int:food_id>')
def edit_food(food_id):
    # Display information about a specific food listing
    # allow the user to edit listing.

    if check_login('Please login to edit your listings.') == 'not_logged_in':
        return redirect('/login')
    else:
        # show user listing and allow them to make changes.
        user = get_user()
        new_messages = get_new_messages(session['user_id'])
        food_listing = Food.query.get(food_id)

        return render_template('editfood.html',
                               food_listing=food_listing,
                               user=user,
                               new_messages=new_messages)


@app.route('/updatelisting', methods=['POST'])
def update_listing():
    # Update an existing listing in the database.

    title = request.form.get('title')
    title = titlecase(title)
    texture = request.form.get('texture')
    datemade = request.form.get('datemade')
    quantity = request.form.get('quantity')
    freshfrozen = request.form.get('freshfrozen')
    description = request.form.get('description')
    allergen_list = request.form.getlist('allergens')
    user_id = session['user_id']
    food_id = request.form.get('food_id')
    deactivate = request.form.get('deactivate')
    allergen_id = request.form.get('allergen_id')
    shared_with_fname = request.form.get('shared_with_fname')
    shared_with_lname = request.form.get('shared_with_lname')

    if deactivate:
        active = False
    else:
        active = True

    this_allergen = Allergen.query.get(allergen_id)
    this_allergen.update_allergen(allergen_id, allergen_list)

    shared_with = shared_with_fname + " " + shared_with_lname

    this_food = Food.query.get(food_id)
    this_food.update_food(food_id, title, texture, datemade, quantity,
                          freshfrozen, description, active, shared_with)

    flash('Your listing has been successfully updated!')

    return redirect('/mylistings')


@app.route('/user/<int:food_user_id>')
def user_info(food_user_id):
    # Displays a specific user's active listings.

    if check_login("Please login to view\
                   this user's listings.") == 'not_logged_in':
        return redirect('/login')
    else:
        # get specific listing from db.
        user = get_user()
        new_messages = get_new_messages(session['user_id'])
        this_user = User.query.get(food_user_id)
        food_listings = Food.query.filter_by(user_id=food_user_id)

        return render_template('user_info.html',
                               this_user=this_user,
                               food_listings=food_listings,
                               user=user,
                               new_messages=new_messages)


@app.route('/messages')
def messages():
    # Displays messages for that specific user.

    if check_login("Please login to view your messages.") == 'not_logged_in':
        return redirect('/login')
    else:
        # Get the messages for that particular user.
        user = get_user()
        new_messages = get_new_messages(session['user_id'])

        unread_messages = get_messages(session['user_id'], False)

        read_messages = get_messages(session['user_id'], True)

        all_messages = unread_messages + read_messages

        return render_template('messages.html',
                               all_messages=all_messages,
                               unread_messages=unread_messages,
                               read_messages=read_messages,
                               user=user,
                               new_messages=new_messages)


@app.route('/send_message', methods=['POST'])
def send_message():
    # Handles sending a message to a specific user.

    # create a message field in the db.
    message = request.form.get('message')
    current_user_id = session['user_id']
    posting_user = request.form.get('posting_user')

    Message.add_message(current_user_id, posting_user, message)

    # Send an alert via sms to the posting
    # user that someone is interested in their food.
    food_listing_id = request.form.get('food_listing')
    food_listing = Food.query.get(food_listing_id)
    poster_name = food_listing.user.fname

    phone_number = food_listing.phone_number
    if phone_number:
        phone_number = "+1"+phone_number
        send_text(phone_number,
                  ("Hi, %s! Someone's interested in your post " +
                   "on Make Less Mush! Sign in and check your " +
                   "messages!") % (poster_name))

    flash('Your message has been sent.')

    return redirect('/home')


@app.route('/delete_message', methods=['POST'])
def change_read_status():
    # Delete a message.

    message_id = request.form.get('message_id')
    message = Message.query.get(message_id)
    message.delete_message()

    user = get_user()
    new_messages = get_new_messages(session['user_id'])

    return jsonify(new_messages=new_messages)


@app.route('/reply_to_message', methods=['POST'])
def reply_to():
    # Reply to a message.

    reply_to_user = request.form['send_message_to']
    current_user = session['user_id']
    message = request.form['message']

    Message.add_message(current_user, reply_to_user, message)

    return "Your message has been sent."


@app.route('/send_text', methods=['POST'])
def send_sms_message():
    # Send an sms to a user about their listing.

    number = request.form.get('number')
    message = request.form.get('message')
    send_text(number, message)

    return "Message sent"


@app.route('/toggle_read', methods=['POST'])
def toggle_read():
    # Mark a message as read or unread in the db.

    message_id = request.form.get('message_id')
    message = Message.query.get(message_id)
    message.toggle_read()
    new_messages = get_new_messages(session['user_id'])

    return jsonify(read_status=message.read_status, new_messages=new_messages)

###############################################################################

PORT = int(os.environ.get("PORT", 5000))
DEBUG = "NO_DEBUG" not in os.environ

if __name__ == "__main__":
    # Set debug to true to have the toolbar extension run.
    app.debug = DEBUG

    connect_to_db(app)

    # Connect our application to our database
    db.init_app(app)

    # Create the tables needed from our model.py (if they already
    # exist, nothing will happen here)
    db.create_all(app=app)

    app.run(host='0.0.0.0', port=PORT)
