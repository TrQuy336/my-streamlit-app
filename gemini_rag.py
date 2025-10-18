# 
import streamlit as st
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
import tempfile
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import google.generativeai as genai
from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv


class PDFChatBot:
    def __init__(self):
        # Load API Key
        load_dotenv()
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            st.error("GOOGLE_API_KEY not found in environment variables.")
            st.stop()
        genai.configure(api_key=api_key)

    # Xử lý file PDF 
    def get_pdf_text(self, pdf_docs):
        """Trích xuất toàn bộ text từ file PDF."""
        text = ""
        try:
            for pdf in pdf_docs:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(pdf.read())
                    tmp_file_path = tmp_file.name

                pdf_reader = PyPDFLoader(tmp_file_path)
                for page in pdf_reader.load_and_split():
                    text += page.page_content
                os.unlink(tmp_file_path)
        except Exception as e:
            st.error(f"Lỗi xử lý PDF: {str(e)}")
            return ""
        return text

    #Chia văn bản thành đoạn
    def get_text_chunks(self, text):
        try:
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=1000)
            chunks = text_splitter.split_text(text)
            return chunks
        except Exception as e:
            st.error(f"Lỗi chia đoạn văn bản: {str(e)}")
            return []

    # Tạo vector store
    def create_vector_store(self, text_chunks):
        try:
            embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
            vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)
            vector_store.save_local("faiss_index")
            st.success("Tài liệu đã được phân tích và lưu vào FAISS index.")
        except Exception as e:
            st.error(f"Lỗi tạo vector store: {str(e)}")

    # Chuỗi QA 
    def get_conversational_chain(self):
        prompt_template = """
        Trả lời câu hỏi một cách chi tiết nhất có thể dựa trên ngữ cảnh được cung cấp.
        Nếu câu trả lời không có trong ngữ cảnh, hãy nói "Câu trả lời không có trong ngữ cảnh."
        Không cung cấp thông tin sai lệch.

        Ngữ cảnh: {context}
        Câu hỏi: {question}

        Answer:
        """
        try:
            model = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.3)
            prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
            chain = load_qa_chain(model, chain_type="stuff", prompt=prompt)
            return chain
        except Exception as e:
            st.error(f"Lỗi khởi tạo QA chain: {str(e)}")
            return None

    # Trả lời người dùng 
    def answer_question(self, user_question):
        try:
            embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
            if not os.path.exists("faiss_index"):
                st.error("Không tìm thấy FAISS index. Hãy tải tài liệu PDF lên trước.")
                return
            new_db = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)
            docs = new_db.similarity_search(user_question)

            chain = self.get_conversational_chain()
            if not chain:
                return

            response = chain(
                {"input_documents": docs, "question": user_question},
                return_only_outputs=True
            )
            st.write("**Trả lời:** ", response["output_text"])
        except Exception as e:
            st.error(f"Lỗi khi trả lời câu hỏi: {str(e)}")

    # Giao diện chính 
    def run(self):
        pdf_docs = st.file_uploader(
            "Tải tài liệu PDF lên",
            accept_multiple_files=True,
            type=["pdf"]
        )
        if st.button("Phân tích tài liệu"):
            if not pdf_docs:
                st.error("Vui lòng tải ít nhất một file PDF.")
                return
            with st.spinner("Đang xử lý tài liệu..."):
                raw_text = self.get_pdf_text(pdf_docs)
                if raw_text:
                    chunks = self.get_text_chunks(raw_text)
                    if chunks:
                        self.create_vector_store(chunks)
                    else:
                        st.error("Không thể chia nội dung PDF.")
                else:
                    st.error("Không đọc được nội dung từ PDF.")

        user_question = st.text_input("Nhập câu hỏi của bạn sau khi tài liệu đã được phân tích:")
        if st.button("Trả lời câu hỏi"):
            if not user_question.strip():
                st.warning("Vui lòng nhập câu hỏi trước khi hỏi.")
                return
            with st.spinner("Đang tìm câu trả lời..."):
                self.answer_question(user_question)
            if user_question:
                self.answer_question(user_question)

    