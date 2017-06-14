# sendCatsWeb
A small app for texting cats to people.
It runs on Python and Flask and psycopg2.
It interfaces with the Twillio API to handle the texting and uses Twitter to find the cats.  

About: In doing this I wanted to experiment a bit more with making a basic application. Its not fancy, but it has most of the moving parts of a web-app. Including using Heroku's schedular to re-populate the cats. I'm sure I could find a better way to find cats, but I wanted to play around with twitter and rates, so let's go with this for a bit. I chose Python because I like it, and frankly, I want to work more with python vs other languages. I should probably figure out passenger for deployment on not heroku. But you could run this on a pi and it would be pretty ok. Anyways. Sending cats via text message on the web is pretty fun. 