# TODO:
# 1. add logger,
# 2. dockerized.
# 3. Add interviewers' personality.


from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Form, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from typing import Optional
import uvicorn
import os
import time
import os
from io import BytesIO
import uuid
import base64
import fitz

from openai import OpenAI
from interviewer import Interviewer
from tutor import Tutor

import tempfile
import shutil
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(override=False)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT = int(os.getenv("PORT"))

STT_FILENAME = "speech.webm"
# client = OpenAI()

app = FastAPI()

# 設定 CORS，允許前端 (通常是 localhost) 存取
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"

# 1. 掛載靜態檔案 (CSS, JS, Images 等)
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


# 2. 設定根路徑直接回傳 index.html
@app.get("/")
async def read_index():
    return FileResponse(FRONTEND_DIR / "index.html")


# 儲存 Session 設定 (In-memory storage)
sessions = {}
interviewer_agents: dict[str, Interviewer] = {}


@app.get("/download_history/{session_id}")
async def download_history(session_id: str):
    if session_id not in interviewer_agents:
        return {"error": "Agent not found."}

    interviewer = interviewer_agents[session_id]

    with tempfile.NamedTemporaryFile(mode="wt", delete=False) as tmp:
        for m in interviewer.message_historys:
            tmp.writelines(f"{m.type:<6}: {m.content}\n" + "-" * 20 + "\n\n")
        tmp.flush()
        return FileResponse(tmp.name, filename=f"history_{session_id}.txt")
    return {"error": "File not found"}


@app.post("/setup")
async def setup_interview(
    name: str = Form(...),
    position: str = Form("Machine Learning Engineer"),
    years_of_experience: float = Form(...),
    interview_type: str = Form(...),
    interviewer_personality: str = Form("friendly"),
    openai_api_key: Optional[str] = Form(OPENAI_API_KEY),
    cv: UploadFile = File(None),
    enable_voice: bool = Form(True),
    # enable_advice: bool = Form(True),
):
    session_id = str(uuid.uuid4())

    cv_filename = None
    cv_str = ""
    if cv:
        cv_content = await cv.read()
        try:
            with fitz.open(stream=cv_content, filetype="pdf") as doc:
                for page in doc:
                    cv_str += page.get_text()
        except Exception as e:
            print(f"Error parsing CV: {e}")

        os.makedirs("uploads", exist_ok=True)
        cv_filename = f"uploads/{session_id}_{cv.filename}"
        with open(cv_filename, "wb") as f:
            f.write(cv_content)

    sessions[session_id] = {
        "name": name,
        "position": position,
        "years_of_experience": years_of_experience,
        "interview_type": interview_type,
        "interviewer_personality": interviewer_personality,
        "openai_api_key": openai_api_key,
        "cv_path": cv_filename,
        "cv_str": cv_str,
        "enable_voice": enable_voice,
        # "enable_advice": enable_advice,
    }
    print(f"Session: {sessions}")
    print(f"config: {sessions[session_id]}")
    print("-" * 20)
    print("cv_str: ", cv_str)

    # raise ValueError()
    return {"session_id": session_id}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, session_id: str = None):
    await websocket.accept()
    print("Client connected")

    config = sessions.get(session_id)
    if not config:
        await websocket.send_text("Error: Invalid Session")
        await websocket.close()
        return
    print(config)

    # initialize LLM clients
    client = OpenAI(api_key=config["openai_api_key"])

    interviewer = Interviewer(config)
    tutor = Tutor(config["openai_api_key"])
    interviewer_agents[session_id] = interviewer
    # init the chatbot.
    response = interviewer.chat("### Start the Interview ###", session_id=session_id)
    current_index = response.index
    await websocket.send_json({"type": "interviewer", "content": response.content, "index": current_index})
    if config.get("enable_voice"):
        await sending_audio_messages(websocket, client, response.content)
    n = 0
    try:
        while True:
            # 接收前端傳來的 JSON 資料
            message = await websocket.receive_json()

            if message.get("type") == "audio":
                data = base64.b64decode(message.get("data"))
                print(f"收到音訊資料，大小: {len(data)} bytes")
                print(type(data))
                # 儲存音訊檔案
                os.makedirs("inputs", exist_ok=True)
                filename = f"inputs/{int(time.time())}-{n}.webm"
                with open(filename, "wb") as f:
                    f.write(data)
                n += 1
                input_text = speech_to_text(client, data)
                await websocket.send_json({"type": "user", "content": input_text, "index": current_index})
                print(f"User said: {input_text}")

                # COMMING QUESTIONS:
                response = interviewer.chat(input_text, session_id=session_id)
                current_index = response.index
                await websocket.send_json({"type": "interviewer", "content": response.content, "index": current_index})

                if config.get("enable_voice"):
                    await sending_audio_messages(websocket, client, response.content)

            elif message.get("type") == "grammar_check":
                data = message.get("data")
                assert "user" in data
                user_message = data["user"]
                index = data["index"]
                response = tutor.improve_grammar(answer=user_message)
                await websocket.send_json({"type": "grammar_check", "content": response, "index": index})

            elif message.get("type") == "generate_ai_answer":
                data = message.get("data")
                assert "user" in data
                assert "interviewer" in data
                user_message = data["user"]
                interviewer_message = data["interviewer"]
                index = data["index"]
                response = tutor.improve_answer(question=interviewer_message, answer=user_message)
                await websocket.send_json({"type": "generate_ai_answer", "content": response, "index": index})

                # print(type(data))
                # print(type(data["user"]))
                # print(message)

            else:

                print("Got websocket message:")
                print(message)

    except WebSocketDisconnect:
        print("Client disconnected")


def speech_to_text(client: OpenAI, input_bytes: bytes) -> str:
    input_file = BytesIO(input_bytes)
    input_file.name = STT_FILENAME
    transcription = client.audio.transcriptions.create(model="gpt-4o-transcribe", file=input_file)
    return transcription.text


async def sending_audio_messages(websocket: WebSocket, client: OpenAI, text: str):
    await websocket.send_text("START_AUDIO")
    tts_response = client.audio.speech.create(model="tts-1", voice="alloy", input=text, response_format="mp3")
    for chunk in tts_response.iter_bytes(chunk_size=4096):
        await websocket.send_bytes(chunk)
    await websocket.send_text("END_AUDIO")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
