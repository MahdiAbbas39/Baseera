import uvicorn
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from pypdf import PdfReader
import io
import os
from groq import Groq

# ==============================================================================
# إعدادات المفتاح (API Key)
# هذا السطر الذكي يقوم بـ:
# 1. البحث عن المفتاح في "Environment Variables" (عشان لما ترفعه على Render).
# 2. إذا لم يجده، يستخدم المفتاح الاحتياطي المكتوب هنا (عشان يشتغل معك في PyCharm).
# ==============================================================================
api_key = os.getenv("GROQ_API_KEY", "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")

client = Groq(api_key=api_key)

app = FastAPI()

# مخزن مؤقت للنص (يتم مسحه عند إعادة تشغيل السيرفر)
project_context = {"text": ""}

# --- واجهة المستخدم (HTML + CSS + JS) ---
html_content = """
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>مستشار المشاريع الذكي (Llama 3.3)</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background-color: #f4f7f6; color: #333; }
        .container { background: white; padding: 30px; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); }
        h1 { color: #2c3e50; text-align: center; margin-bottom: 25px; }

        /* تصميم صندوق الرفع */
        .upload-box { border: 2px dashed #3498db; padding: 30px; text-align: center; background: #ecf0f1; border-radius: 10px; cursor: pointer; transition: 0.3s; margin-bottom: 20px; }
        .upload-box:hover { background: #d6eaf8; border-color: #2980b9; }
        .upload-box p { margin: 10px 0 0; font-weight: bold; color: #7f8c8d; }

        /* منطقة الشات */
        .chat-box { border: 1px solid #ddd; padding: 20px; height: 400px; overflow-y: auto; background: #fff; border-radius: 10px; margin-bottom: 20px; box-shadow: inset 0 2px 5px rgba(0,0,0,0.05); }
        .message { margin: 10px 0; padding: 12px 18px; border-radius: 10px; max-width: 80%; line-height: 1.6; position: relative; }
        .user { background: #3498db; color: white; margin-right: auto; text-align: left; border-bottom-left-radius: 2px; }
        .bot { background: #f1f0f0; color: #2c3e50; margin-left: auto; border-bottom-right-radius: 2px; }

        /* منطقة الإدخال */
        .input-area { display: flex; gap: 10px; }
        input[type="text"] { flex: 1; padding: 15px; border: 1px solid #ccc; border-radius: 8px; outline: none; transition: 0.3s; }
        input[type="text"]:focus { border-color: #3498db; box-shadow: 0 0 5px rgba(52, 152, 219, 0.3); }
        button { background-color: #2ecc71; color: white; padding: 12px 30px; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; font-size: 16px; transition: 0.3s; }
        button:hover { background-color: #27ae60; }
        button:disabled { background-color: #bdc3c7; cursor: not-allowed; }

        /* تحسينات للجوال */
        @media (max-width: 600px) {
            body { padding: 10px; }
            .container { padding: 15px; }
            .message { max-width: 90%; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>مستشار المشاريع الذكي 🚀</h1>
        <p style="text-align: center; color: #7f8c8d; margin-bottom: 20px;">مدعوم بمحرك Llama 3.3 السريع</p>

        <div class="upload-box" onclick="document.getElementById('fileInput').click()">
            <h3>📂 اضغط لرفع ملف المشروع (PDF)</h3>
            <input type="file" id="fileInput" style="display:none" onchange="uploadFile()">
            <p id="status">لم يتم اختيار ملف</p>
        </div>

        <div id="chatBox" class="chat-box">
            <div class="message bot">مرحباً! أنا جاهز لتحليل مشاريعك. ارفع ملف PDF وسأجيبك عن أي تفاصيل داخله (الميزانية، الوقت، النطاق...).</div>
        </div>

        <div class="input-area">
            <input type="text" id="userMsg" placeholder="اكتب سؤالك هنا..." disabled onkeypress="if(event.key==='Enter') sendMessage()">
            <button id="sendBtn" onclick="sendMessage()" disabled>إرسال</button>
        </div>
    </div>

    <script>
        async function uploadFile() {
            const fileInput = document.getElementById('fileInput');
            const status = document.getElementById('status');
            if (!fileInput.files[0]) return;

            const formData = new FormData();
            formData.append("file", fileInput.files[0]);

            status.textContent = "جاري التحليل...";
            status.style.color = "#e67e22";

            try {
                const res = await fetch("/upload", { method: "POST", body: formData });
                const data = await res.json();
                if (res.ok) {
                    status.innerHTML = "✅ " + data.message;
                    status.style.color = "green";
                    document.getElementById('userMsg').disabled = false;
                    document.getElementById('sendBtn').disabled = false;
                    document.getElementById('fileInput').value = ""; // تفريغ الملف
                } else {
                    status.textContent = "❌ خطأ: " + data.detail;
                    status.style.color = "red";
                }
            } catch (e) {
                status.textContent = "❌ فشل الاتصال بالسيرفر";
                status.style.color = "red";
            }
        }

        async function sendMessage() {
            const input = document.getElementById('userMsg');
            const chatBox = document.getElementById('chatBox');
            const text = input.value.trim();
            if (!text) return;

            // إضافة رسالة المستخدم
            chatBox.innerHTML += `<div class="message user">${text}</div>`;
            input.value = "";
            chatBox.scrollTop = chatBox.scrollHeight;

            // مؤشر التحميل
            const loadingId = "loading-" + Date.now();
            chatBox.innerHTML += `<div id="${loadingId}" class="message bot">... جاري التفكير</div>`;
            chatBox.scrollTop = chatBox.scrollHeight;

            try {
                const res = await fetch("/chat", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ message: text })
                });
                const data = await res.json();

                document.getElementById(loadingId).remove();

                // تنسيق الرد (تحويل الأسطر الجديدة إلى <br>)
                const formattedReply = data.reply.replace(/\\n/g, "<br>");
                chatBox.innerHTML += `<div class="message bot">${formattedReply}</div>`;

            } catch (e) {
                document.getElementById(loadingId).innerText = "حدث خطأ في الاتصال";
            }
            chatBox.scrollTop = chatBox.scrollHeight;
        }
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def get_ui():
    return html_content


@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    try:
        # التحقق من نوع الملف
        if not file.filename.endswith('.pdf'):
            return {"message": "يرجى رفع ملف PDF فقط!"}

        content = await file.read()
        pdf_reader = PdfReader(io.BytesIO(content))

        # استخراج النصوص من كل الصفحات
        text = ""
        for page in pdf_reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"

        if not text.strip():
            return {"message": "الملف يبدو فارغاً أو يحتوي على صور فقط (غير قابل للقراءة النصية)."}

        # حفظ النص في الذاكرة
        project_context["text"] = text
        return {"message": f"تم استيعاب الملف ({len(pdf_reader.pages)} صفحات) بنجاح! تفضل بالسؤال."}

    except Exception as e:
        return {"message": f"حدث خطأ أثناء قراءة الملف: {str(e)}"}


class ChatMessage(BaseModel):
    message: str


@app.post("/chat")
async def chat(msg: ChatMessage):
    if not project_context["text"]:
        return {"reply": "⚠️ لم يتم رفع أي ملف بعد. يرجى رفع ملف PDF أولاً."}

    try:
        # إرسال الطلب إلى Groq (Llama 3.3)
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": f"""
                    أنت مساعد ذكي ومتخصص في إدارة المشاريع. 
                    مهمتك هي الإجابة على أسئلة المستخدم بناءً **فقط** على محتوى المستند المقدم أدناه.

                    --- بداية المستند ---
                    {project_context['text'][:25000]} 
                    --- نهاية المستند ---

                    تعليمات:
                    1. أجب باللغة العربية بوضوح.
                    2. إذا كانت المعلومة غير موجودة في المستند، قل "لا توجد معلومات حول ذلك في الملف".
                    3. كن مختصراً ومباشراً.
                    """
                },
                {
                    "role": "user",
                    "content": msg.message
                }
            ],
            # الموديل الجديد والفعال حالياً
            model="llama-3.3-70b-versatile",
            temperature=0.3,  # درجة حرارة منخفضة لضمان الدقة
            max_tokens=1024,
        )
        return {"reply": chat_completion.choices[0].message.content}

    except Exception as e:
        return {"reply": f"حدث خطأ في الاتصال مع الذكاء الاصطناعي: {str(e)}"}


if __name__ == "__main__":
    # تشغيل السيرفر على جميع الواجهات (مهم لـ Render وللوصول المحلي)
    uvicorn.run(app, host="0.0.0.0", port=8000)