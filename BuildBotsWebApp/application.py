from flask import Flask, render_template
from views.twitter import twitter_blueprint
from views.discord import discord_blueprint
from views.shell import shell_blueprint


application = Flask(__name__)
with open('website_key.txt') as wk:
    application.secret_key = wk.read()
application.register_blueprint(twitter_blueprint)
application.register_blueprint(discord_blueprint)
application.register_blueprint(shell_blueprint)


@application.route('/', methods=['GET'])
def home():
    return render_template('home.html')


if __name__ == '__main__':
    application.run(debug=True)
