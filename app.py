from flask import *
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options  
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service

app = Flask(__name__)
app.secret_key = os.urandom(32)

try:
    FLAG = open('./flag.txt', 'r').read()

except:
    FLAG = '[**FLAG**]'

login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, username, password):
        self.username = username
        self.password = password
    def get_id(self):
        return self.username

users = {
    "admin":generate_password_hash(FLAG),
    "guest":generate_password_hash("guest123")
}

@login_manager.user_loader
def load_user(user_id):
    return User(user_id, users.get(user_id))

bulletin_messages = [{
    "seq": 0,
    "title": "flag",
    "author": "admin",
    "content": FLAG
}]

def read_url(url, params, username="admin", password=None):
    try:
        capabilities = DesiredCapabilities.CHROME
        capabilities['goog:loggingPrefs'] = {'performance': 'ALL'}
        service = Service(executable_path="/app/chromedriver-linux64/chromedriver")
        options = webdriver.ChromeOptions()
        for _ in [
            "headless",
            "disable-gpu",
            "no-sandbox",
            "disable-dev-shm-usage",
        ]:
            options.add_argument(_)
        driver = webdriver.Chrome(service=service, options=options)
        if username and password:
            driver.get("https://ecs-winner.chals.io/login")
            element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            element.send_keys(username)
            element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "password"))
            )
            element.send_keys(password)
            element.submit()
        driver.get(url)
        max_wait_time = 10000
        WebDriverWait(driver, max_wait_time).until(
            EC.presence_of_element_located((By.TAG_NAME, 'body'))
        )
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

    
@app.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for('bulletin_board'))
    else:
        return redirect(url_for('login'))

@app.route("/login", methods=["GET", "POST"])
def login():
    """"
    if request.method == "GET":
        if current_user.is_authenticated:
            return redirect(url_for('bulletin_board'))
        return render_template("login.html")
    
    if current_user.is_authenticated:
        return redirect(url_for('bulletin_board'))
    """
    username = request.form.get("username")
    password = request.form.get("password")

    user = users.get(username)

    if user and check_password_hash(user, password):
        user_obj = User(username, user)
        login_user(user_obj)
        return redirect(url_for('bulletin_board'))
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    if request.method == "POST":
        if current_user.is_authenticated:
            return redirect(url_for('login'))
        username = request.form.get("username")
        password = request.form.get("password")

        if users.get(username):
            return "Username already exists."
        else:
            users[username] = generate_password_hash(password)
            user_obj = User(username, users[username])
            user_obj.id = user_obj.get_id()
            login_user(user_obj)
            return redirect(url_for('login'))
    return render_template("register.html")

@app.route("/changepw", methods=["POST"])
def changepw():
    userid = request.form.get("userid")
    userpw = request.form.get("userpw")

    if userid in users:
        old_password_hash = users[userid]
        users[userid] = generate_password_hash(userpw)
        return redirect(url_for('login'))
    
    return render_template("changepw.html", msg="false")

@app.route("/logout")
@login_required
def logout():
    bulletin_messages.clear()
    bulletin_messages.append({
        "seq": 0,
        "title": "flag",
        "author": "admin",
        "content": FLAG
    })
    logout_user()
    return redirect(url_for("login"))

@app.route("/bulletin_board", methods=["GET"])
@login_required
def bulletin_board():
    boardlist = []
    for message in bulletin_messages:
        if message["author"] == current_user.username or message["author"] == "admin":
            boardlist.append(message)
    return render_template("bulletin_board.html", messages=boardlist)

@app.route("/bulletin_content/<int:message_id>")
@login_required
def bulletin_content(message_id):
    if 0 <= message_id < len(bulletin_messages):
        message = bulletin_messages[message_id]
        if current_user.username == "admin":
            return render_template("bulletin_content_admin.html", content=message["content"])
        elif current_user.username == message["author"]:
            return render_template("bulletin_content.html", content=message["content"])
        else:
            return '<script>alert("You are not authorized to view this message.");history.go(-1);</script>'
    return "Invalid message ID"

@app.route("/write", methods=["GET", "POST"])
@login_required
def write():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    if request.method == "GET":
        return render_template("write.html")
    else:
        new_title = request.form.get("new_title")
        new_content = request.form.get("new_content")
        new_content = xss_check(new_content)
        new_message = {"title": new_title, "content": new_content, "author": current_user.username}
        bulletin_messages.append(new_message)
        return redirect(url_for('bulletin_board'))

def xss_check(content):
    xss_filter = ["script", "frame", "obejct", "data", "alert","fetch","XMLHttpRequest","eval"]
    for _ in xss_filter:
         content = content.replace(_, "*")
    return content 

@app.route("/read_request/<int:message_id>")
@login_required
def read_request(message_id):
    if 0 <= message_id < len(bulletin_messages):
        message = bulletin_messages[message_id]
        if current_user.username == message["author"]:
            url = f"https://ecs-winner.chals.io/bulletin_content/{message_id}"
            admin_password = FLAG
            result = read_url(url, {"name": "admin", "value": generate_password_hash(admin_password)}, username="admin", password=admin_password)
            if result:
                return "Read request successfully sent!"
            else:
                return "Error in sending read request."
        else:
            return "You are not authorized to send a read request for this message."
    return "Invalid message ID"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
