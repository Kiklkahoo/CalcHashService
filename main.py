import flask
import json
import smtplib
import threading
import os
import configparser
import hashlib
import urllib.request
import shutil

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import urllib.request

app = flask.Flask(__name__)

task_states = ["task does not exist", "work on a task in progress", "task completed", "task failed"]


class TaskThread(threading.Thread):
    def __init__(self, url, email, task_name):
        threading.Thread.__init__(self, name=task_name)
        self.daemon = False
        self.task_name = task_name
        self.interval = 1
        self.url = url
        self.email = email
        self.state = task_states[1]

    def run(self):
        file_name = self.download_file(self.url)
        if file_name == None:
            self.state = task_states[3]
            return

        self.calced_hash = self.calc_hash(file_name)
        if self.calced_hash == None:
            self.state = task_states[3]
            return

        if self.email != None:
            email_result = self.send_email(self.email, self.url, self.calced_hash)
            if email_result == None:
                self.state = task_states[3]
                return

        self.state = task_states[2]

    def load_config(self):
        config = configparser.ConfigParser()
        config.read("config.ini")

        sender_mail = config.get("Settings", "email")
        sender_pass = config.get("Settings", "password")

        return sender_mail, sender_pass


    def download_file(self, url):
        try:
            if not os.path.exists("download\\"):
                os.mkdir("download\\")
            downloaded_file_name = "download\\" + str(self.task_name)
            with urllib.request.urlopen(url) as response, open(downloaded_file_name, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
            return downloaded_file_name
        except:
            return None

    def calc_hash(self, file):
        try:
            buf_size = 65536

            md5 = hashlib.md5()
            print(str(file))

            with open(str(file), 'rb') as f:
                while True:
                    data = f.read(buf_size)
                    if not data:
                        break
                    md5.update(data)
            return str(md5.hexdigest())
        except:
            return None


    def send_email(self, email, url, hash):
        try:
            addr_from, password = self.load_config()
            addr_to = str(email)


            msg = MIMEMultipart()
            msg['From'] = addr_from
            msg['To'] = addr_to
            msg['Subject'] = 'Hash for your file'

            body = str(url) + " " + str(hash)
            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP_SSL('smtp.gmail.com:465')
            server.ehlo()

            server.login(addr_from, password)
            server.send_message(msg)
            server.quit()
            return "done"
        except:
            return None


all_tasks = []


def to_json(data):
    return json.dumps(data) + "\n"


def resp(code, data):
    return flask.Response(
        status=code,
        mimetype="application/json",
        response=to_json(data)
    )


def post_request_validate():
    url = flask.request.form['url']
    try:
        email = flask.request.form['email']
    except:
        email = None
    free_num = len(all_tasks)

    new_task = TaskThread(url, email, "Task_%s" % free_num)
    all_tasks.append(new_task)

    new_task.start()
    return new_task.task_name


def get_request_validate():
    task_id = flask.request.args.get('id')
    return task_id


def find_task_by_name(name):
    returned_value = None
    for gg in range(len(all_tasks)):
        if str(name) == str(all_tasks[gg].task_name):
            returned_value = all_tasks[gg]
    return returned_value


@app.route('/')
def index():
    return "Hi, It is Sultan Feizov's test task"


@app.route('/submit', methods=['POST'])
def post_theme():
    task_by_request = post_request_validate()
    return resp(200, {"id": task_by_request})


@app.route('/check', methods=['GET'])
def get():
    try:
        result_task = find_task_by_name(get_request_validate())

        if result_task == None:
            return resp(404, {"status": task_states[0]})

        elif result_task.state == task_states[2]:
            return resp(200, {
                "md5": result_task.calced_hash,
                "status": result_task.state,
                "url": result_task.url
            })
        else:
            return resp(200, {"status": str(result_task.state)})

    except:
        return flask.abort(404)


if __name__ == "__main__":
    app.run(debug=False)
