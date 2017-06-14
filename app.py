### IMPORTS ####################################################################

### sys stuff ##

import random, sys, json, datetime, re, os, unicodedata
from random import choice


### twilio stuff ###
import twilio
import twilio.rest
import twilio.twiml
from twilio.rest import TwilioRestClient

### flask ###

from flask import Flask, render_template, request, redirect, url_for, flash

### twython ###

from twython import Twython, TwythonError

### db stuff  ###
import psycopg2
import urlparse

### FLASK SETUP  ####################################################################

app = Flask(__name__, static_folder='static',static_url_path='/static')
app.config['DEBUG'] = True
app.config['TRAP_BAD_REQUEST_ERRORS'] = True

### ALL THE F**KING KEYS ####################################################################

### for heroku

app.secret_key = os.environ['APP_KEY']

TWIL_TOKEN = os.environ['TWIL_TOKEN']
TWIL_SID = os.environ['TWIL_SID']
TWILIO_NUMBER = os.environ['TWILIO_NUMBER']

client = TwilioRestClient(TWIL_SID, TWIL_TOKEN)

TWIT_KEY = os.environ['TWIT_KEY']
TWIT_SECRET = os.environ['TWIT_SECRET']
OAUTH_TOKEN = os.environ['OAUTH_TOKEN']
OAUTH_TOKEN_SECRET = os.environ['OAUTH_TOKEN_SECRET']

twitter = Twython(TWIT_KEY, TWIT_SECRET, OAUTH_TOKEN, OAUTH_TOKEN_SECRET)

### DATABASE CONNECTION ################################################################

###  heroku's set up ###

urlparse.uses_netloc.append("postgres")
url = urlparse.urlparse(os.environ["DATABASE_URL"])

con = None

try:

	con = psycopg2.connect(
	    database=url.path[1:],
	    user=url.username,
	    password=url.password,
	    host=url.hostname,
	    port=url.port
	)
	cur = con.cursor()
except psycopg2.DatabaseError, e:
	if con:
		con.rollback()
	print 'Error %s' % e

### GET YO CATS FROM TWITTER ##############################################################

def getCat():

	### try to pull the cats for the day

	cats =[]
	
	try:
		user_timeline = twitter.get_user_timeline(screen_name='FullCatHouse', count=200)		
	except TwythonError as e:
		print e

	tweets = user_timeline
	
	### get the media URL from the tweet, only if the media_url exists ####
	for tweet in tweets:
		if 'media' in tweet['entities'].keys():
			media = tweet['entities']['media']
			for mediaItem in media:
				if 'media_url' in mediaItem.keys():
					zeCat = mediaItem['media_url']
					scrubbed = unicodedata.normalize('NFKD', zeCat).encode('UTF-8','ignore')
					if not 'tweet_video_thumb' in scrubbed:
						cats.append(scrubbed)						
	return cats

### SEND YO' CATS TO THE DB ##############################################################

### Used in the scheduler, runs at midnight, gets fresh cats ###

def sendCatsToDatabase():
	
	### get your cats from getCat ####

	catsToInstert = [] # a mutable list full of tuples of cats....uh...
	catsfromTweets = getCat()

	for index, cat in enumerate(catsfromTweets, start=1): ### ohmygod...*dies of happiness*
		catsToInstert.append((index, cat))

	### insert those furry bastards into the database ####

	cur.execute("DROP TABLE IF EXISTS Cats")
	cur.execute("CREATE TABLE cats(Id INTEGER PRIMARY KEY, URL VARCHAR(100))")
	query = "INSERT INTO Cats (Id, URL) VALUES (%s, %s)"
	cur.executemany(query, catsToInstert)
	con.commit()


### GET A RANDOM CAT FROM THE DB ##############################################################

def getRandomCat():

	cur.execute("SELECT * FROM Cats ORDER BY RANDOM() LIMIT 1;") #I've only got up to 200 rows so this might be ok, tho not ideal
	rows = cur.fetchall()
	fetchedCat = rows[0][1]
	return fetchedCat

### THE COUNTER  #############################################################################

def writeCountToDatabase(counter):
	c = str(counter)
	cur.execute("UPDATE Counter SET count=%s ", [c])
	con.commit()
	
def readCounter():
	cur.execute("SELECT * FROM Counter")
	rows = cur.fetchall()
	fetchedCount = rows[0][0]
	return fetchedCount


### APP VIEWS ####################################################################

@app.route("/",methods=['GET','POST'])

def main():

	counter = int(readCounter()) #read from databse
	maxCats = 100
	catsLeft = maxCats - counter
	
	if (counter < maxCats):
		return render_template('form.html', catsLeft=catsLeft) 
	else:
		return render_template('sorry.html')


@app.route("/submit-form", methods = ['POST'])

def sendCat():

	### check to see if you're human ###
	
	isBot = request.form['pot']
	
	if isBot:  #if this has data in it	
		flash("I think you are perhaps not a human!")
		return redirect(url_for('main'))
	else:
		makeNumber = request.form['areaCode'] + request.form['exchange'] + request.form['ending']
		number = re.sub(r'[^\w]','',makeNumber) #strip punctuation and spaces
		senderName = request.form['name']

		if senderName:
			if len(number) == 10:
				try:
					number = int(number) # value checks to make sure it is an int
					### pull a cat from database
					singleCat = getRandomCat()

					### format number and set up body
					formattedNumber = "+1" + str(number)
					print formattedNumber
					mediaBody = "Cat Delivery from %s! =^.^=" % senderName
					print mediaBody
					
					### try sending it via twilio
					
					try:
						client.messages.create(to=formattedNumber, 
							from_=TWILIO_NUMBER,
							body=mediaBody, 
							media_url=[singleCat])
						print "sent cat"

					except twilio.TwilioRestException as e:
						print e
						return redirect(url_for('oops'))
					
					### counter ###
					x = int(readCounter())
					x += 1
					writeCountToDatabase(x)

					return redirect(url_for('thankYou'))
					
				except ValueError:
					flash("Sorry, you can not use characters")
					return redirect(url_for('main'))
			else:
				flash("Sorry, you seem to have missed a number")
				return redirect(url_for('main'))
		else:
			flash("You must have a name")
			return redirect(url_for('main'))


### THANKS AND OOOOOOPS ####################################################################

@app.route("/thanks", methods=['GET'])
def thankYou():
	return render_template('thanks.html')

@app.route("/oops", methods=['GET'])
def oops():
	return render_template('oops.html')

### RESPONSE IF SOMEONE TEXTS BACK ####################################################################

@app.route("/inbound", methods=['GET', 'POST'])
def accept_response():
	message = "This cat was sent to you by a friend through Random Cat Sender. http://sendcats.herokuapp.com/ you can stop receiving these if you text back stop"
	resp = twilio.twiml.Response()
	resp.sms(message)
	return str(resp)

### RUN IT ####################################################################

if __name__ == '__main__': # If we're executing this app from the command line
    app.run(debug=True)