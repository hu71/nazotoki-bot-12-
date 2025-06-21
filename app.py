import os
from flask import Flask, request, render_template, redirect
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, ImageMessage, TextSendMessage, StickerMessage
from linebot.exceptions import InvalidSignatureError

app = Flask(__name__)
line_bot_api = LineBotApi('00KCkQLhlaDFzo5+UTu+/C4A49iLmHu7bbpsfW8iamonjEJ1s88/wdm7Yrou+FazbxY7719UNGh96EUMa8QbsGBf9K5rDWhJpq8XTxakXRuTM6HiJDSmERbIWfyfRMfscXJPcRyTL6YyGNZxqkYSAQdB04t89/1O/w1cDnyilFU=')  # ← ここは自分のトークンに置き換える
handler = WebhookHandler('6c12aedc292307f95ccd67e959973761')         # ← ここも自分のシークレットに置き換える

user_states = {}
pending_users = []

questions = [
    "第1問: 鍵は赤い箱の中。写真で答えてね！",
    "第2問: 机の裏を探してみよう。写真で答えてね！",
    "第3問: 黒板に書かれた数字に注目。写真で答えてね！",
    "第4問: 窓の外にヒントがあるよ。写真で答えてね！",
    "第5問: 最後の謎はあなたの直感！写真で答えてね！"
]

hints = [
    "赤い箱の中に何があるか見てみよう！",
    "机の裏のメモをよく読んで！",
    "数字の順番がヒント！",
    "外の風景に答えが隠れてるかも！",
    "今までの謎を思い出してみよう！"
]

@app.route("/")
def hello_world():
    return "LINE Bot Running!"

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        return "Invalid signature", 400

    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    user_id = event.source.user_id
    text = event.message.text.strip()

    # 初回登録
    if user_id not in user_states:
        user_states[user_id] = {"name": None, "stage": 0}

    state = user_states[user_id]

    # 名前登録
    if state["name"] is None:
        state["name"] = text
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"{text}さん、参加ありがとう！\n{questions[0]}"))
        return

    # 「ヒント」
    if text == "ヒント":
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=hints[state["stage"]]))
        return

    # 「リタイア」
    if text == "リタイア":
        state["stage"] += 1
        if state["stage"] >= len(questions):
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="謎の解説を送るよ！\n文化祭ありがとう！"))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"謎の解説を送ったよ。\n次はこちら！\n{questions[state['stage']]}"))
        return

    # 特殊ワード
    if text == "1=∞":
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="そんなわけないだろ亀ども"))
        return
    if text.endswith("？"):
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="good question!"))
        return

    # それ以外無反応
    return

@handler.add(MessageEvent, message=StickerMessage)
def handle_sticker(event):
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="何の意味があるの？"))

@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    user_id = event.source.user_id
    if user_id not in user_states:
        return

    os.makedirs("static/images", exist_ok=True)
    message_content = line_bot_api.get_message_content(event.message.id)
    image_path = f"static/images/{user_id}.jpg"
    with open(image_path, "wb") as f:
        for chunk in message_content.iter_content():
            f.write(chunk)

    if user_id not in pending_users:
        pending_users.append(user_id)

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="画像を受け取りました！判定をお待ちください。"))

@app.route("/form", methods=["GET"])
def show_form():
    users = []
    for user_id in pending_users:
        name = user_states[user_id]["name"]
        stage = user_states[user_id]["stage"] + 1
        users.append({
            "user_id": user_id,
            "name": name,
            "stage": stage,
            "image": f"/static/images/{user_id}.jpg"
        })
    return render_template("judge.html", users=users)

@app.route("/judge", methods=["POST"])
def judge():
    user_id = request.form["user_id"]
    result = request.form["result"]
    state = user_states[user_id]

    if result == "correct":
        state["stage"] += 1
        if state["stage"] == len(questions):
            line_bot_api.push_message(user_id, TextSendMessage(text="おめでとう！謎解きクリア！エンディング分岐だ！"))
        else:
            line_bot_api.push_message(user_id, TextSendMessage(text="大正解！次の問題に進むよ！\n" + questions[state["stage"]]))
    else:
        line_bot_api.push_message(user_id, TextSendMessage(text="残念、不正解。もう一度考えてみよう。「ヒント」と送ってみてね！"))

    if user_id in pending_users:
        pending_users.remove(user_id)

    return redirect("/form")
