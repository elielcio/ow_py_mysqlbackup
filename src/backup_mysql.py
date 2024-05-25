import os
import subprocess
import boto3
from datetime import datetime, timedelta
import schedule
import time
import pymysql
import configparser
import sys

# Verificar se o arquivo de configuração existe
try:
    with open('config.ini') as f:
        pass
except FileNotFoundError:
    print("Erro: O arquivo de configuração 'config.ini' não foi encontrado.")
    sys.exit(1)

# Carregar configurações do arquivo config.ini
config = configparser.ConfigParser()
config.read('config.ini')


# Acessar configurações
DB_HOST = config['mysql']['DB_HOST']
DB_PORT = config.getint('mysql', 'DB_PORT', fallback=3306)  # Porta padrão 3306 se não estiver definida
DB_USER = config['mysql']['DB_USER']
DB_PASS = config['mysql']['DB_PASS']
BACKUP_DIR = config['backup']['BACKUP_DIR']
OBJECT_STORAGE_BUCKET = config['object_storage']['OBJECT_STORAGE_BUCKET']
OBJECT_STORAGE_URL = config['object_storage']['OBJECT_STORAGE_URL']
AWS_ACCESS_KEY = config['object_storage']['AWS_ACCESS_KEY']
AWS_SECRET_KEY = config['object_storage']['AWS_SECRET_KEY']

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
