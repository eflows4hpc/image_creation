from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, logout_user
from builder_service import db, User, check_and_log_user, CAPTCHA_SERVER_KEY, CAPTCHA_WEBSITE_KEY
import requests
import json

auth = Blueprint('auth', __name__)

@auth.route('/login')
def login():
    return render_template('login.html')

@auth.route('/login', methods=['POST'])
def login_post():
    username = request.form.get('username')
    password = request.form.get('password')
    remember = True if request.form.get('remember') else False
    if check_and_log_user(username, password, remember):
        return redirect(url_for('dashboard.home'))
    else:
        flash('Please check your login details and try again.')
        return redirect(url_for('auth.login')) 
    
   

@auth.route('/signup')
def signup():
    return render_template('signup.html', web_site_key=CAPTCHA_WEBSITE_KEY)

@auth.route('/signup', methods=['POST'])
def signup_post():
    email = request.form.get('email')
    username = request.form.get('username')
    password = request.form.get('password')
    retype_password = request.form.get('retype_password')
    captcha_response = request.form.get('g-recaptcha-response')
    if captcha_response is None:
        flash("Please, validate captcha")
        return redirect(url_for('auth.signup'))
    if not captcha_validation(captcha_response):
        flash("Please, incorrect captcha validation")
        return redirect(url_for('auth.signup'))
    if username is None or password is None or retype_password is None or email is None:
        flash('Email, username or password is not provided')
        return redirect(url_for('auth.signup'))    
    if User.query.filter_by(username=username).first() is not None:
        flash('User already exists')
        return redirect(url_for('auth.signup'), login=True)  
    user = User(username=username, email=email)
    user.hash_password(password)
    db.session.add(user)
    db.session.commit()
    return redirect(url_for('auth.login'))

def captcha_validation(captcha_response):
    secret = CAPTCHA_SERVER_KEY
    payload = {'response':captcha_response, 'secret':secret}
    response = requests.post("https://www.google.com/recaptcha/api/siteverify", payload)
    response_text = json.loads(response.text)
    print("reCaptcha Response: " + str(response_text))
    return response_text['success']


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logout Successful")
    return redirect(url_for('auth.login'))