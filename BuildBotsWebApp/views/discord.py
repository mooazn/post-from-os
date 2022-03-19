from flask import Blueprint, render_template

discord_blueprint = Blueprint('discord', __name__, template_folder='templates')


@discord_blueprint.route('/discord')
def discord():
    return render_template('discord.html')
