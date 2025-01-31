from flask import Flask, request, abort

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *

#======python的函數庫==========
import tempfile, os
import datetime
import openai
import time
import traceback
#======python的函數庫==========

app = Flask(__name__)
static_tmp_path = os.path.join(os.path.dirname(__file__), 'static', 'tmp')
# Channel Access Token
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
# Channel Secret
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))
# OPENAI API Key初始化設定
global aiClient,messageQueue
aiClient = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
messageQueue = [
    {
              "role": "developer",
              "content": [
                {
                  "type": "text",
                  "text": '你是一個C#的助理，請用專業語氣提供我答案'
                }
              ]
    }
]


def GPT_response(text):
    global aiClient,messageQueue
    
    # 新增使用者的輸入訊息到 messageQueue
    messageQueue.append({
        "role": "user",
        "content": text
    })
    
    # 接收回應
    completion = aiClient.chat.completions.create(
        model="gpt-4o",
        store=True,
        messages = messageQueue
    )
    answer = completion.choices[0].message.content.strip()
    print(answer)

    # 將助手回應追加到 messageQueue
    messageQueue.append({
        "role": "assistant",
        "content": answer
    })

    # 控制 messageQueue 長度，保留最多 10 筆記錄
    if len(messageQueue) > 10:
        messageQueue.pop(1)  # 刪除第二筆（保留第一筆系統提示）
                                                 

    return answer


# 監聽所有來自 /callback 的 Post Request
@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']
    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'


# 處理訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text
    global messageQueue

    #功能切換
    # 檢查特殊指令以切換角色
    if msg == "CSharp工作":
        messageQueue[0] = {
            "role": "system",
            "content": "你是一個C#工作的助理，請用專業語氣回答使用者的問題(繁體中文)。"
        }
        reply_message = "角色已切換為 C# 工作助理。請繼續輸入您的問題。"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(reply_message))
        return
        
    elif msg == "英文老師":
        messageQueue[0] = {
            "role": "system",
            "content": "你是一個英文老師，請將使用者的訊息翻譯成英文，並提供更好的表達方式與文法修正(繁體中文)。"
        }
        reply_message = "角色已切換為英文老師。請輸入您要翻譯或修正的內容。"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(reply_message))
        return
    
    try:
        GPT_answer = GPT_response(msg)   

        # 訊息切分
        max_length = 5000  # LINE 單則訊息的上限
        messages = []

        # 將訊息切分為每段最多 5000 字元
        while len(GPT_answer) > max_length:
            messages.append(GPT_answer[:max_length])
            GPT_answer = GPT_answer[max_length:]
        messages.append(GPT_answer)  # 加入剩下的訊息段

        # 逐段傳送回應
        for msg_part in messages:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(msg_part))
        
    except:
        print(traceback.format_exc())
        line_bot_api.reply_message(event.reply_token, TextSendMessage('你所使用的OPENAI API key額度可能已經超過，請於後台Log內確認錯誤訊息'))
        

@handler.add(PostbackEvent)
def handle_message(event):
    print(event.postback.data)


@handler.add(MemberJoinedEvent)
def welcome(event):
    uid = event.joined.members[0].user_id
    gid = event.source.group_id
    profile = line_bot_api.get_group_member_profile(gid, uid)
    name = profile.display_name
    message = TextSendMessage(text=f'{name}歡迎加入')
    line_bot_api.reply_message(event.reply_token, message)
        
        
import os
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
