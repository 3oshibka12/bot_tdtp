import boto3
import uuid
import io

# Подключаемся к нашему локальному S3 (Minio)
s3_client = boto3.client(
    's3',
    endpoint_url='http://minio:9000',
    aws_access_key_id='minioadmin',       # Логин из docker-compose
    aws_secret_access_key='minioadmin123' # Пароль из docker-compose
)

BUCKET_NAME = 'dating-photos'

def upload_photo_to_s3(file_bytes: io.BytesIO) -> str:
    """Загружает байты картинки в S3 бакет и возвращает ссылку"""
    # Проверяем, есть ли бакет, если нет - создаем
    try:
        s3_client.create_bucket(Bucket=BUCKET_NAME)
    except Exception:
        pass 
    
    filename = f"{uuid.uuid4()}.jpg"
    
    # Загружаем файл
    s3_client.put_object(
        Bucket=BUCKET_NAME, 
        Key=filename, 
        Body=file_bytes.getvalue()
    )
    
    # Возвращаем "ссылку" (в реальном мире это был бы публичный URL)
    return f"s3://{BUCKET_NAME}/{filename}"

def get_photo_from_s3(s3_url: str) -> bytes | None:
    """Скачивает фото из S3 и возвращает в виде байтов"""
    if not s3_url or not s3_url.startswith("s3://"):
        return None
        
    try:
        # Превращаем 's3://dating-photos/123.jpg' в bucket и key
        parts = s3_url.replace("s3://", "").split("/")
        bucket = parts[0]
        key = parts[1]
        
        # Достаем файл из хранилища
        response = s3_client.get_object(Bucket=bucket, Key=key)
        return response['Body'].read()
    except Exception as e:
        print(f"Ошибка скачивания из S3: {e}")
        return None