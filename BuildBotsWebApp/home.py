from flask import Flask, render_template, request
from flask_wtf import Form
from wtforms import StringField
from wtforms.validators import DataRequired


class TestForm(Form):
    your_name = StringField('', [DataRequired()])
    last_name = StringField('', [DataRequired()])


app = Flask(__name__)
app.secret_key = 'super secret key'


@app.route('/')
def home():
    return render_template('home.html', path=app.root_path)


@app.route('/twitter', methods=['GET', 'POST'])
def twitter():
    form = TestForm(request.form)
    if request.method == 'POST' and form.validate():
        yn = form.your_name.data.strip()
        ln = form.last_name.data.strip()
        if yn != 'Mo' or ln != 'Mo':
            return render_template('twitter.html', form=form, error='Invalid Name')
        return '<h1> {} </h1>'.format(yn)
    return render_template('twitter.html', form=form)


@app.route('/discord')
def discord():
    return render_template('discord.html')


if __name__ == '__main__':
    app.run(debug=True)
