import twython
from flask import Blueprint, render_template, request, flash, redirect, session, url_for
import requests
from requests.structures import CaseInsensitiveDict
from twython import Twython
from werkzeug.utils import secure_filename
from wtforms.validators import DataRequired
from wtforms import Form, StringField

twitter_blueprint = Blueprint('twitter', __name__, template_folder='templates')


class TraitForm(Form):
    need_traits = StringField('Print Traits?', [DataRequired()])


@twitter_blueprint.route('/twitter', methods=['GET', 'POST'])
def twitter():
    try:
        _ = session['_flashes']
        return redirect(url_for('twitter.twitter'))
    except KeyError:
        pass
    form = TraitForm(request.form)
    if request.method == 'POST' and form.validate():
        traits_needed = str(form.need_traits.data.strip())
        traits_needed = traits_needed.lower()
        need_traits = False
        if traits_needed != 'y' and traits_needed != 'n' and traits_needed != 'true' and traits_needed != 'false' and\
                traits_needed != 't' and traits_needed != 'f' and traits_needed != 'yes' and traits_needed != 'no':
            return render_template('twitter.html', form=form, invalid_file='Please enter a true/false or yes/no value.')
        if traits_needed == 'y' or traits_needed == 'yes' or traits_needed == 'true' or traits_needed == 't':
            need_traits = True
        file = request.files['filename']
        if file:
            if not secure_filename(file.filename).endswith('.txt'):
                return render_template('twitter.html', form=form, invalid_file='Invalid file type. Only .txt is '
                                                                               'allowed.')
            else:
                parsed = parse_file(file)
                if not parsed:
                    pass
                else:
                    session['random'] = 'value'
                    session['need_traits'] = need_traits
                    session['content'] = parsed[1]
                    return redirect(url_for('shell.shell'))
        else:
            return render_template('twitter.html', form=form, invalid_file='Please provide a .txt file.')
    return render_template('twitter.html', form=form)


def parse_file(file):
    flash(f'Beginning validation of Twitter Values File named \"{file.filename}\"...', 'normal')
    num_lines = 0
    file_content = []
    for line in file.stream.readlines():
        num_lines += 1
        file_content.append(str(line.decode('utf-8')))
    if num_lines != 8:
        flash('Invalid number of lines. Only 8 lines are allowed. Please follow the format.', 'error')
        return False
    flash(f'Evaluating hashtags...', 'normal')
    hashtags_test = file_content[0].strip()
    hashtags = 0
    words_in_hash_tag = hashtags_test.split()
    if hashtags_test != 'None':
        if len(words_in_hash_tag) == 0:
            flash('Incorrect hashtag format. Leave as \"None\" if you do not want hashtags.', 'error')
            return False
        if len(hashtags_test) >= 120:
            flash('Too many characters in hashtags.', 'error')
            return False
        if len(words_in_hash_tag) > 10:
            flash('Too many hashtags.', 'error')
            return False
        for word in words_in_hash_tag:
            if word[0] == '#':
                hashtags += 1
        if hashtags != len(words_in_hash_tag):
            flash('All words must be preceded by a hashtag (#).', 'error')
            return False
    flash('Hashtags validated.', 'inner')
    flash('Evaluating collection...', 'normal')
    collection_name_test = file_content[1].strip()
    test_collection_name_url = 'https://api.opensea.io/api/v1/collection/{}'.format(collection_name_test)
    test_response = requests.get(test_collection_name_url)
    if test_response.status_code != 200:
        flash('The provided collection name does not exist.', 'error')
        return False
    flash('Collection validated.', 'inner')
    flash('Evaluating Twitter Account...', 'normal')
    api_key = file_content[2].strip()
    api_key_secret = file_content[3].strip()
    access_token = file_content[4].strip()
    access_token_secret = file_content[5].strip()
    twitter_test = Twython(
        api_key,
        api_key_secret,
        access_token,
        access_token_secret
    )
    try:
        twitter_test.verify_credentials()
        twitter_test.client.close()
    except twython.exceptions.TwythonAuthError:
        twitter_test.client.close()
        flash('Invalid Twitter Keys supplied.', 'error')
        return False
    flash('Twitter credentials validated.', 'inner')
    flash('Evaluating Opensea API key...', 'normal')
    test_os_key = file_content[6].strip()
    test_os_key_url = 'https://api.opensea.io/api/v1/events?only_opensea=false'
    test_os_headers = CaseInsensitiveDict()
    test_os_headers['Accept'] = 'application/json'
    test_os_headers['x-api-key'] = test_os_key
    test_os_response = requests.get(test_os_key_url, headers=test_os_headers)
    if test_os_response.status_code != 200:
        flash('Invalid OpenSea API key supplied.', 'error')
        return False
    flash('OpenSea Key validated.', 'inner')
    flash('Evaluating Etherscan API Key', 'normal')
    test_ether_scan_values = file_content[7].strip().split()
    test_ether_scan_key = test_ether_scan_values[0]
    test_ether_scan_url = 'https://api.etherscan.io/api?module=gastracker&action=gasoracle&apikey={}'. \
        format(test_ether_scan_key)
    test_ether_scan_response = requests.get(test_ether_scan_url)
    if test_ether_scan_response.json()['message'] == 'NOTOK':
        flash('Invalid Ether Scan key.', 'error')
        return False
    flash('Ether Scan key validated.', 'inner')
    flash('Validation complete. No errors found.', 'normal')
    return [True, file_content]
