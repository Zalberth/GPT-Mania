from flask import Flask, render_template, request, jsonify
from Foundation import NSAppleScript
import time
from threading import Thread
import threading
import jwt

# 用于JWT的密钥，实际应用中请保密
SECRET_KEY = "Secret-Key"


incoming_request_No = 0
# 定义锁对象
counterlock = threading.Lock()

count_down = 5

max_length = 100


##  escape转义
def escape_string(input_text):
    escape_map = {
        "\n": "",
        "\r": "",
        "\t": "",
        "\"": "\\\"",
        "\'": "\\\'",
        "`": "\\\`",
        "{": "\\\{",
        "}": "\\\}",
    }
    for k, v in escape_map.items():
        input_text = input_text.replace(k, v)
    return input_text


def SendChaGPTRequest(input_text):
    applescript_str = """
    -- 指定要输入的文字
    set inputText to "{input_text}"

    -- 在Chrome中查找第一个textarea元素，输入指定的文字，并模拟回车键的JavaScript代码
    set jsCode to "
        var textarea = document.querySelector('textarea');
        textarea.value = " & quoted form of inputText & ";
        var event = new KeyboardEvent('keydown', {{
            key: 'Enter',
            code: 'Enter',
            which: 13,
            keyCode: 13,
            bubbles: true,
            cancelable: true
        }});
        textarea.dispatchEvent(event);
    "

    -- 执行上述脚本
    tell application "Google Chrome"
        -- 确保Chrome正在运行且至少有一个窗口打开
        if not (exists window 1) then return "没有打开的窗口"

        -- 获得当前活动标签页
        set activeTab to active tab of window 1

        -- 在当前活动标签页中执行JavaScript
        execute activeTab javascript jsCode
    end tell
    """.format(input_text=input_text)
    script = NSAppleScript.alloc().initWithSource_(applescript_str)
    success, error = script.executeAndReturnError_(None)
    if success is None:
        print("Error:", error)



def GetChatResponse():
    ### 获取返回值
    aps_str_get_res = """
        -- 在Chrome中查找具有特定class的div标签，并返回最后一个符合条件的标签中的内容的JavaScript代码
        set jsCode to "
            var elements = document.querySelectorAll('div.markdown.prose.w-full.break-words');
            var lastElement = elements[elements.length - 1];
            lastElement ? lastElement.innerHTML : '';
        "

        -- 执行上述脚本
        tell application "Google Chrome"
            -- 确保Chrome正在运行且至少有一个窗口打开
            if not (exists window 1) then return "没有打开的窗口"

            -- 获得当前活动标签页
            set activeTab to active tab of window 1

            -- 在当前活动标签页中执行JavaScript，并获取返回的内容
            set elementContent to execute activeTab javascript jsCode
        end tell

        return elementContent
    """
    print("ready to grab response")
    script = NSAppleScript.alloc().initWithSource_(aps_str_get_res)
    element_content = ""
    success, error = script.executeAndReturnError_(None)
    print("grabing response")
    if success is None:
        print("Error:", error)
        element_content="--"
    else:
        #print("element_content" : element_content)
        element_content = str(success.stringValue())

    # for i in range(4):
    #     time.sleep(5)
    #     success, error = script.executeAndReturnError_(None)
    #     print("grabing response")
    #     if success is None:
    #         print("Error:", error)
    #     else:
    #         #print("element_content" : element_content)
    #         element_content = str(success.stringValue())

    return element_content


# todo 需要一个看门狗线程，如果countdown长时间维持一个小于5的值，就将它变回5，这个时长设置为60s


app = Flask(__name__,static_folder='static')

# 主页
@app.route('/', methods=['GET', 'POST'])
def home():
    client_ip = request.remote_addr
    client_port = request.environ.get('REMOTE_PORT')
    print("Incoming IP :", client_ip, " Port: ", client_port)
    token = jwt.encode({'ip': client_ip, 'port': client_port}, SECRET_KEY, algorithm='HS256')
    print("token: ", token)
    return render_template('index.html')

# 发送请求的GPT问题
@app.route("/send_chat_question", methods=['GET', 'POST'])
def postYourQuestion():
    response = {"output_text": "请稍后再试...", "possessed": True}
    # # 加锁
    # counterlock.acquire()
    # # 访问计数器变量
    # global incoming_request_No
    # if incoming_request_No == 1:
    #     # 释放锁
    #     counterlock.release()
    #     return jsonify(response)
    # incoming_request_No += 1
    # # 释放锁
    # counterlock.release()
    response = {"output_text": "处理中...", "possessed": False}

    # 解析token
    auth_header = request.headers.get('Authorization')
    if auth_header:
        token = auth_header.split(" ")[1]
        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            print("received token: ", token)
            print("port in token : ", data['port'])
        except jwt.exceptions.InvalidTokenError:
            abort(401)
    else:
        abort(401)


    if request.method == 'POST':
        input_text = request.form['text']        
        input_text = escape_string(input_text)
        length = len(input_text.encode('utf-8').decode('unicode_escape'))
        if len(input_text.encode('utf-8').decode('unicode_escape')) > max_length:
            input_text = input_text[:max_length] + "..."
        print("postYourQuestion = input text:", input_text)
        SendChaGPTRequest(input_text)
        print("text sent")
        return jsonify(response)
    return jsonify(response)


# jwt token
@app.route('/token', methods=['GET'])
def token():
    client_ip = request.remote_addr
    client_port = request.environ.get('REMOTE_PORT')

    token = jwt.encode({'ip': client_ip, 'port': client_port}, SECRET_KEY, algorithm='HS256')
    return jsonify({'token': token})


@app.route("/my_gpt_ans", methods=['GET', 'POST'])
def getGPTRes():
    response = {"output_text": "处理中..."}
    if request.method == 'GET':
        # global count_down
        # # 有可能丢失请求
        # count_down -= 1
        # 使用多线程来执行耗时操作
        output_text = GetAndSendResponse()
        #print("current ans:", output_text)
        # 异步处理请求
        response = {"output_text": output_text}
        # print("counter_down :", count_down)

        # if count_down <= 0:
        #     # 加锁
        #     counterlock.acquire()
        #     # 访问计数器变量
        #     global incoming_request_No
        #     incoming_request_No = 0
        #     # 释放锁
        #     counterlock.release()   

        #     count_down = 5         

        # 返回 JSON 格式的响应，不需要渲染模板
        return jsonify(response)
    return jsonify(response)

def GetAndSendResponse():
    result = GetChatResponse()
    print("response get")
    return result
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8099)
