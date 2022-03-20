from flask import Blueprint, render_template, session, redirect, url_for, request
from wtforms import Form, StringField
from wtforms.validators import DataRequired

shell_blueprint = Blueprint('shell', __name__, template_folder='templates')


class TestForm(Form):
    username = StringField('Username:', [DataRequired()])


@shell_blueprint.route('/shell', methods=['GET', 'POST'])
def shell():
    try:
        _ = session['random']
    except KeyError:
        return redirect(url_for('twitter.twitter'))
    content = [c.strip() for c in session['content']]
    need_traits = session['need_traits']
    form = TestForm(request.form)
    if request.method == 'POST' and form.validate():
        print(form.username.data.strip())
        session.pop('_flashes')
        session.pop('random')
        session.pop('content')
        session.pop('need_traits')
    return render_template('shell.html', form=form)
