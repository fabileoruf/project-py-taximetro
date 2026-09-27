FROM python:3.14-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 TAXIMETRO_DATA=/data
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --uid 10001 --create-home taxi \
    && mkdir /data && chown taxi:taxi /data
COPY taximetro ./taximetro
COPY config.json taximeter.py ./
USER taxi
EXPOSE 8080
CMD ["python", "-m", "taximetro", "web", "--host", "0.0.0.0", "--port", "8080"]
