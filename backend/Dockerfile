FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --timeout 120 --retries 5 -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
COPY . .
EXPOSE 8000
COPY start.sh .
RUN chmod +x start.sh
CMD ["./start.sh"]
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "8"]
# CMD ["python", "init_db.py", "&&", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "8"]
# CMD ["/bin/sh", "-c", "python init_db.py && uvicorn main:app --host 0.0.0.0 --port 8000 --workers 8"]
