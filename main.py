import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI
from langchain.chains import RetrievalQA

# إعداد التطبيق
app = FastAPI()

# السماح للواجهة بالاتصال بالخلفية
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# تعيين مفتاح API (يجب وضعه هنا أو في متغيرات البيئة)
# os.environ["OPENAI_API_KEY"] = "sk-..." 

# المتغيرات العالمية لتخزين "المعرفة"
vector_store = None
qa_chain = None


class QuestionRequest(BaseModel):
    question: str


@app.on_event("startup")
async def startup_event():
    global vector_store, qa_chain
    # هنا يمكننا تحميل ملفات افتراضية إذا وجدت
    print("System Started. Ready to load documents.")


@app.post("/upload/")
async def upload_document(file: UploadFile = File(...)):
    global vector_store, qa_chain

    # 1. حفظ الملف مؤقتاً
    file_location = f"temp_{file.filename}"
    with open(file_location, "wb+") as file_object:
        file_object.write(file.file.read())

    # 2. قراءة الملف وتقسيمه
    loader = PyPDFLoader(file_location)
    documents = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    texts = text_splitter.split_documents(documents)

    # 3. إنشاء قاعدة البيانات المتجهة (RAG Core)
    embeddings = OpenAIEmbeddings()
    vector_store = FAISS.from_documents(texts, embeddings)

    # 4. إعداد سلسلة السؤال والجواب
    llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vector_store.as_retriever()
    )

    return {"message": "تم تحليل الملف بنجاح! يمكنك الآن طرح الأسئلة."}


@app.post("/ask/")
async def ask_question(request: QuestionRequest):
    global qa_chain
    if qa_chain is None:
        raise HTTPException(status_code=400, detail="الرجاء رفع ملف أولاً")

    response = qa_chain.run(request.question)
    return {"answer": response}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)