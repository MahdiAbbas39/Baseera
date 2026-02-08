import uvicorn
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pypdf import PdfReader
import io
import os
from groq import Groq
from dotenv import load_dotenv

# تحميل البيئة
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

# إعداد العميل
client = Groq(api_key=api_key)

app = FastAPI()

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# 1. الصفحة الرئيسية: تقرأ ملف index.html
@app.get("/", response_class=HTMLResponse)
async def home():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

# 2. رفع الملف: يستخرج النص ويرجعه للمتصفح
@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    try:
        content = await file.read()
        reader = PdfReader(io.BytesIO(content))
        text = ""
        for page in reader.pages:
            extract = page.extract_text()
            if extract: text += extract + "\n"
        
        # نرجع النص للمتصفح ليحفظه عنده (حل مشكلة Vercel)
        return {"text": text}
    except Exception as e:
        return {"error": str(e)}

# 3. الشات: يستقبل السؤال + النص
class ChatReq(BaseModel):
    message: str
    context: str

@app.post("/chat")
async def chat(req: ChatReq):
    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": f"Answer based on context:\n{req.context[:25000]}"},
                {"role": "user", "content": req.message}
            ],
            model="llama-3.3-70b-versatile",
        )
        return {"reply": completion.choices[0].message.content}
    except Exception as e:
        return {"reply": f"Error: {str(e)}"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
