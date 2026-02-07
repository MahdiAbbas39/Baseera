import uvicorn
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pypdf import PdfReader
import io
import os
from groq import Groq

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

project_context = {"text": ""}

# --- التعديل هنا: قراءة ملف index.html ---
@app.get("/", response_class=HTMLResponse)
def get_ui():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

# --- باقي الكود كما هو ---
@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    try:
        if not file.filename.endswith('.pdf'):
            return {"message": "يرجى رفع ملف PDF فقط!"}
        content = await file.read()
        pdf_reader = PdfReader(io.BytesIO(content))
        text = ""
        for page in pdf_reader.pages:
            extracted = page.extract_text()
            if extracted: text += extracted + "\n"
        
        if not text.strip(): return {"message": "الملف فارغ!"}
        project_context["text"] = text
        return {"message": "تم التحليل بنجاح"}
    except Exception as e:
        return {"message": f"خطأ: {str(e)}"}

class ChatMessage(BaseModel):
    message: str

@app.post("/chat")
async def chat(msg: ChatMessage):
    if not project_context["text"]:
        return {"reply": "⚠️ يرجى رفع ملف PDF أولاً من القائمة الجانبية."}
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": f"أنت مساعد ذكي. أجب بناءً على النص:\n{project_context['text'][:25000]}"
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

