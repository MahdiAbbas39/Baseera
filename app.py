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

load_dotenv()

# إعداد المفتاح
api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ❌ حذفنا المتغير global project_context لأنه ما ينفع مع Vercel

@app.get("/", response_class=HTMLResponse)
async def get_ui():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    return "Error: index.html not found"

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    try:
        content = await file.read()
        pdf_reader = PdfReader(io.BytesIO(content))
        text = ""
        for page in pdf_reader.pages:
            extracted = page.extract_text()
            if extracted: text += extracted + "\n"
        
        # ✅ التغيير هنا: نرسل النص المستخرج للمتصفح
        return {"message": "تم التحليل بنجاح", "extracted_text": text}
    except Exception as e:
        return {"message": f"خطأ: {str(e)}"}

# ✅ التغيير هنا: نطلب من المتصفح يرسل النص مع السؤال
class ChatMessage(BaseModel):
    message: str
    context: str = ""  # النص يجينا من المتصفح

@app.post("/chat")
async def chat(msg: ChatMessage):
    # نستخدم النص اللي وصلنا في الطلب
    if not msg.context:
        return {"reply": "⚠️ يرجى رفع ملف PDF أولاً."}
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": f"أنت مساعد ذكي. أجب بناءً على النص التالي:\n{msg.context[:25000]}"
                },
                { "role": "user", "content": msg.message }
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.3,
        )
        return {"reply": chat_completion.choices[0].message.content}
    except Exception as e:
        return {"reply": f"خطأ: {str(e)}"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
