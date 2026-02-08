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

# --- فحص المفتاح ---
api_key = os.getenv("GROQ_API_KEY")
print(f"DEBUG: API Key Loaded? {bool(api_key)}") # طباعة حالة المفتاح في السيرفر

if api_key:
    client = Groq(api_key=api_key)
else:
    client = None

app = FastAPI()

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

html_content = """
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>بصيرة | Debug Mode</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Cairo', sans-serif; padding: 20px; text-align: center; }
        .box { border: 2px dashed #ccc; padding: 20px; margin: 20px auto; max-width: 400px; border-radius: 10px; }
        button { padding: 10px 20px; background: #0084ff; color: white; border: none; border-radius: 5px; cursor: pointer; }
        #log { color: red; font-weight: bold; margin-top: 20px; }
    </style>
</head>
<body>
    <h1>وضع التشخيص 🕵️‍♂️</h1>
    
    <div class="box">
        <h3>1. اختبار المفتاح</h3>
        <button onclick="checkKey()">هل المفتاح موجود؟</button>
    </div>

    <div class="box">
        <h3>2. رفع الملف</h3>
        <input type="file" id="fileInput">
        <button onclick="uploadFile()">رفع وتحليل</button>
    </div>

    <div class="box">
        <h3>3. تجربة الشات</h3>
        <input type="text" id="msg" placeholder="اكتب أي شيء...">
        <button onclick="sendChat()">إرسال</button>
    </div>

    <div id="log"></div>

    <script>
        let storedText = "";

        // دالة لإظهار الأخطاء
        function logError(msg) {
            document.getElementById('log').innerText = "❌ الخطأ: " + msg;
            alert("❌ خطأ: " + msg);
        }

        async function checkKey() {
            try {
                const res = await fetch("/debug-key");
                const data = await res.json();
                if (data.status === "ok") alert("✅ المفتاح موجود ويعمل!");
                else logError("المفتاح غير موجود في السيرفر! تأكد من Environment Variables");
            } catch (e) { logError(e.message); }
        }

        async function uploadFile() {
            const file = document.getElementById('fileInput').files[0];
            if (!file) return alert("اختر ملفاً أولاً");

            const formData = new FormData();
            formData.append("file", file);

            try {
                const res = await fetch("/upload", { method: "POST", body: formData });
                const data = await res.json();
                if (data.error) {
                    logError(data.error);
                } else {
                    storedText = data.text;
                    alert("✅ تم استخراج النص بنجاح! عدد الحروف: " + storedText.length);
                }
            } catch (e) { logError("فشل الرفع: " + e.message); }
        }

        async function sendChat() {
            const msg = document.getElementById('msg').value;
            if (!storedText) return logError("لا يوجد نص محفوظ! ارفع الملف أولاً.");
            
            try {
                const res = await fetch("/chat", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ message: msg, context: storedText })
                });
                const data = await res.json();
                if (data.error) logError(data.error);
                else alert("✅ الرد: " + data.reply);
            } catch (e) { logError("فشل الشات: " + e.message); }
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def home():
    return html_content

@app.get("/debug-key")
def debug_key():
    if api_key: return {"status": "ok"}
    return {"status": "missing"}

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    try:
        content = await file.read()
        reader = PdfReader(io.BytesIO(content))
        text = ""
        for page in reader.pages:
            extract = page.extract_text()
            if extract: text += extract
        
        if not text.strip():
            return {"error": "الملف فارغ أو لم نستطع قراءة النص منه (ربما هو صورة؟)"}
            
        return {"text": text}
    except Exception as e:
        return {"error": f"خطأ سيرفر أثناء الرفع: {str(e)}"}

class ChatReq(BaseModel):
    message: str
    context: str

@app.post("/chat")
async def chat(req: ChatReq):
    if not client:
        return {"error": "المفتاح غير موجود في السيرفر!"}
    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": f"Context:\n{req.context[:15000]}"},
                {"role": "user", "content": req.message}
            ],
            model="llama-3.3-70b-versatile",
        )
        return {"reply": completion.choices[0].message.content}
    except Exception as e:
        return {"error": f"خطأ من Groq: {str(e)}"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
