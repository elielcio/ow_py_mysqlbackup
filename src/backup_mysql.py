import os
import subprocess
import boto3
from datetime import datetime, timedelta
import schedule
import time
import pymysql

# Configurações
DB_HOST = "localhost"
DB_USER = "seu_usuario"
DB_PASS = "sua_senha"
BACKUP_DIR = "/home/ow_py_mysqlbackup/backups"
OBJECT_STORAGE_BUCKET = "ow-bk-db-01"
OBJECT_STORAGE_URL = "https://usc1.contabostorage.com/ow-bk-db-01"
AWS_ACCESS_KEY = "seu_access_key"
AWS_SECRET_KEY = "seu_secret_key"
IGNORED_DATABASES = {"information_schema", "performance_schema", "mysql", "sys"}

# Inicializa o cliente S3
s3_client = boto3.client(
    's3',
    endpoint_url=OBJECT_STORAGE_URL,
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY
)

def get_databases():
    """Obtém a lista de bancos de dados existentes no MySQL local."""
    connection = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASS)
    cursor = connection.cursor()
    cursor.execute("SHOW DATABASES")
    databases = [db[0] for db in cursor.fetchall()]
    cursor.close()
    connection.close()
    return databases

def backup_mysql():
    """Realiza o backup de todos os bancos de dados MySQL e envia para o Object Storage."""
    databases = get_databases()
    for db_name in databases:
        if db_name in IGNORED_DATABASES:
            continue
        
        # Data e hora para o nome do arquivo
        date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_file = f"{BACKUP_DIR}/backup_{db_name}_{date_str}.sql.gz"

        # Realiza o backup e comprime
        with open(backup_file, 'wb') as f:
            subprocess.run(
                ["mysqldump", "-h", DB_HOST, "-u", DB_USER, f"-p{DB_PASS}", db_name],
                stdout=subprocess.PIPE,
                check=True
            ).stdout

        # Envia para o Object Storage
        s3_client.upload_file(backup_file, OBJECT_STORAGE_BUCKET, os.path.basename(backup_file))
        print(f"Backup realizado e enviado para o Object Storage com sucesso: {backup_file}")

def cleanup_old_backups():
    """Limpa backups antigos, mantendo backups a cada 15 minutos das últimas 24 horas e um backup diário dos últimos 7 dias."""
    now = datetime.now()
    backups = s3_client.list_objects_v2(Bucket=OBJECT_STORAGE_BUCKET).get('Contents', [])
    
    for backup in backups:
        backup_time = datetime.strptime(backup['Key'].split('_')[-1].replace('.sql.gz', ''), "%Y-%m-%d_%H-%M-%S")
        # Backups mais antigos que 7 dias
        if backup_time < now - timedelta(days=7):
            s3_client.delete_object(Bucket=OBJECT_STORAGE_BUCKET, Key=backup['Key'])
            print(f"Backup deletado: {backup['Key']}")
        # Backups mais antigos que 24 horas mas dentro de 7 dias, manter um por dia
        elif backup_time < now - timedelta(hours=24):
            daily_backup_time = backup_time.replace(hour=0, minute=0, second=0, microsecond=0)
            if (backup_time - daily_backup_time).total_seconds() >= 86400:  # Backups mais antigos que 24 horas
                s3_client.delete_object(Bucket=OBJECT_STORAGE_BUCKET, Key=backup['Key'])
                print(f"Backup deletado: {backup['Key']}")

# Agendar backups a cada 15 minutos
schedule.every(15).minutes.do(backup_mysql)
# Agendar limpeza diária dos backups
schedule.every().day.at("00:00").do(cleanup_old_backups)

# Executa a programação
while True:
    schedule.run_pending()
    time.sleep(1)
