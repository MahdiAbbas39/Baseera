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

# تحميل المفاتيح
load_dotenv()
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

# --- كود التصميم (HTML + CSS + JS) مدمج هنا للسهولة ---
html_content = """
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>بصيرة | Baseera</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    
    <style>
        :root { --primary: #0084ff; --bg: #f4f7f6; }
        body { font-family: 'Cairo', sans-serif; background: var(--bg); margin: 0; height: 100vh; display: flex; overflow: hidden; }
        
        /* القائمة الجانبية */
        .sidebar { width: 350px; background: white; padding: 20px; border-left: 1px solid #ddd; display: flex; flex-direction: column; gap: 20px; }
        .logo { font-size: 24px; font-weight: bold; color: var(--primary); text-align: center; margin-bottom: 10px; }
        
        .upload-box { 
            border: 2px dashed #ccc; padding: 30px; text-align: center; 
            border-radius: 10px; cursor: pointer; transition: 0.3s; background: #fafafa;
        }
        .upload-box:hover { border-color: var(--primary); background: #eef7ff; }
        
        /* معاينة PDF */
        #pdf-preview { flex: 1; border: 1px solid #eee; border-radius: 8px; display: none; background: #333; }
        iframe { width: 100%; height: 100%; border: none; }

        /* الشات */
        .main-chat { flex: 1; display: flex; flex-direction: column; background: #fff; }
        .chat-container { flex: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 15px; }
        .message { max-width: 80%; padding: 12px 18px; border-radius: 15px; line-height: 1.6; }
        .bot { background: #f0f2f5; color: black; align-self: flex-end; }
        .user { background: var(--primary); color: white; align-self: flex-start; }
        
        .input-area { padding: 20px; border-top: 1px solid #ddd; display: flex; gap: 10px; }
        input { flex: 1; padding: 15px; border: 1px solid #ddd; border-radius: 30px; outline: none; }
        button { padding: 10px 25px; background: var(--primary); color: white; border: none; border-radius: 30px; cursor: pointer; }
        
        /* للجوال */
        @media (max-width: 768px) { body { flex-direction: column; } .sidebar { width: 100%; height: 200px; } }
    </style>
</head>
<body>

    <div class="sidebar">
        <div class="logo"><i class="fas fa-eye"></i> بصيرة</div>
        
        <div class="upload-box" onclick="document.getElementById('fileInput').click()">
            <i class="fas fa-cloud-upload-alt fa-2x"></i>
            <h3>رفع ملف PDF</h3>
            <p id="status" style="font-size: 12px; color: #666;">اضغط للاختيار</p>
            <input type="file" id="fileInput" hidden onchange="uploadFile()">
        </div>

        <div id="pdf-preview">
            <iframe id="pdf-frame"></iframe>
        </div>
    </div>

    <div class="main-chat">
        <div class="chat-container" id="chatBox">
            <div class="message bot">مرحباً! 👋 ارفع ملف المشروع وسأحفظه في المتصفح لتسألني عنه في أي وقت.</div>
        </div>
        <div class="input-area">
            <input type="text" id="msgInput" placeholder="اكتب سؤالك هنا..." onkeypress="if(event.key==='Enter') send()">
            <button onclick="send()"><i class="fas fa-paper-plane"></i></button>
        </div>
    </div>

    <script>
        let storedText = ""; // هنا سنحفظ النص داخل المتصفح

        async function uploadFile() {
            const fileInput = document.getElementById('fileInput');
            const status = document.getElementById('status');
            const file = fileInput.files[0];
            if (!file) return;

            // 1. عرض المعاينة
            const url = URL.createObjectURL(file);
            document.getElementById('pdf-frame').src = url;
            document.getElementById('pdf-preview').style.display = 'block';

            // 2. إرسال للسيرفر لاستخراج النص
            const formData = new FormData();
            formData.append("file", file);
            status.innerText = "جاري التحليل...";

            try {
                const res = await fetch("/upload", { method: "POST", body: formData });
                const data = await res.json();
                
                if (res.ok) {
                    storedText = data.text; // ✅ حفظ النص في المتغير
                    status.innerText = "✅ تم الحفظ بنجاح";
                    status.style.color = "green";
                    addMsg("bot", "✅ استلمت الملف وحفظت محتواه! يمكنك سؤالي الآن.");
                } else {
                    status.innerText = "❌ خطأ";
                }
            } catch (e) { status.innerText = "❌ فشل الاتصال"; }
        }

        async function send() {
            const input = document.getElementById('msgInput');
            const text = input.value.trim();
            if (!text) return;
            
            // تأكد من وجود نص محفوظ
            if (!storedText) {
                addMsg("bot", "⚠️ يرجى رفع ملف PDF أولاً.");
                return;
            }

            addMsg("user", text);
            input.value = "";
            addMsg("bot", "...");

            try {
                // ✅ نرسل النص المحفوظ مع السؤال
                const res = await fetch("/chat", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ message: text, context: storedText }) 
                });
                const data = await res.json();
                
                // حذف نقاط الانتظار وإضافة الرد
                document.querySelector(".bot:last-child").innerHTML = data.reply.replace(/\\n/g, "<br>");
            } catch (e) {
                document.querySelector(".bot:last-child").innerText = "❌ حدث خطأ";
            }
        }

        function addMsg(cls, txt) {
            const div = document.createElement("div");
            div.className = "message " + cls;
            div.innerHTML = txt;
            document.getElementById("chatBox").appendChild(div);
            document.getElementById("chatBox").scrollTop = 10000;
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def home():
    return html_content

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    try:
        content = await file.read()
        reader = PdfReader(io.BytesIO(content))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        
        # ✅ نرجع النص للمتصفح ليحفظه عنده
        return {"text": text}
    except Exception as e:
        return {"error": str(e)}

class ChatReq(BaseModel):
    message: str
    context: str # ✅ نستقبل النص مع كل رسالة

@app.post("/chat")
async def chat(req: ChatReq):
    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": f"Answer based on this text:\n{req.context[:25000]}"},
                {"role": "user", "content": req.message}
            ],
            model="llama-3.3-70b-versatile",
        )
        return {"reply": completion.choices[0].message.content}
    except Exception as e:
        return {"reply": f"Error: {str(e)}"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
