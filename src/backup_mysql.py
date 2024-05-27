import os
import glob
import subprocess
import boto3
from datetime import datetime, timedelta
import schedule
import time
import pymysql
import configparser
import sys
import logging


# Configurando o log
logging.basicConfig(filename='/var/log/ow_py_mysqlbackup.log', level=logging.INFO)

# Obter o diretório do script
script_dir = os.path.dirname(os.path.realpath(__file__))
# Navegar para o diretório pai
parent_dir = os.path.dirname(script_dir)
# Caminho para o arquivo config.ini
config_file = os.path.join(parent_dir, 'config.ini')

# Verificar se o arquivo de configuração existe
print("Verificando se o arquivo de configuração 'config.ini' existe...")
try:
    with open(config_file) as f:
        pass
except FileNotFoundError:
    print("Erro: O arquivo de configuração 'config.ini' não foi encontrado.")
    sys.exit(1)
else:
    print("Arquivo de configuração 'config.ini' encontrado.")

# Carregar configurações do arquivo config.ini
print("Carregando configurações do arquivo 'config.ini'...")
config = configparser.ConfigParser()
config.read(config_file)

# Acessar configurações
DB_HOST = config['mysql']['DB_HOST']
DB_PORT = config.getint('mysql', 'DB_PORT', fallback=3306)  # Porta padrão 3306 se não estiver definida
DB_USER = config['mysql']['DB_USER']
DB_PASS = config['mysql']['DB_PASS']
IGNORED_DATABASES = [db.strip() for db in config['ignored_databases']['IGNORED_DATABASES'].split(',')]

BACKUP_DIR = config['backup']['BACKUP_DIR']
OBJECT_STORAGE_BUCKET = config['object_storage']['OBJECT_STORAGE_BUCKET']
OBJECT_STORAGE_URL = config['object_storage']['OBJECT_STORAGE_URL']
AWS_ACCESS_KEY = config['object_storage']['AWS_ACCESS_KEY']
AWS_SECRET_KEY = config['object_storage']['AWS_SECRET_KEY']
SYNC_WITH_OBJECT_STORAGE = config['object_storage'].getboolean('SYNC_WITH_OBJECT_STORAGE', fallback=False)

DAILY_RETENTION = config['retention'].getint('DAILY_RETENTION', fallback=7)
LAST_BACKUPS_RETENTION = config['retention'].getint('LAST_BACKUPS_RETENTION', fallback=24)
BACKUP_INTERVAL_MINUTES = config['schedule'].getint('BACKUP_INTERVAL_MINUTES', fallback=15)


print("Configurações carregadas com sucesso!")

# Inicializa o cliente S3 se sincronização estiver ativada
if SYNC_WITH_OBJECT_STORAGE:
    print("Inicializando cliente S3...")
    s3_client = boto3.client(
        's3',
        endpoint_url=OBJECT_STORAGE_URL,
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY
    )
    print("Cliente S3 inicializado com sucesso!")

def get_databases():
    """Obtém a lista de bancos de dados existentes no MySQL local."""
    print("Obtendo a lista de bancos de dados existentes no MySQL local...")
    connection = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASS)
    cursor = connection.cursor()
    cursor.execute("SHOW DATABASES")
    databases = [db[0] for db in cursor.fetchall()]
    cursor.close()
    connection.close()
    print("Lista de bancos de dados obtida com sucesso!")
    return databases

def backup_mysql():
    """Realiza o backup de todos os bancos de dados MySQL e envia para o Object Storage se sincronização estiver ativada."""
    print("Iniciando o backup de todos os bancos de dados MySQL...")
    databases = get_databases()
    for db_name in databases:
        if db_name in IGNORED_DATABASES:
            continue
        
        # Data e hora para o nome do arquivo
        date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_file = f"{BACKUP_DIR}/backup_{db_name}_{date_str}.sql"

        # Realiza o backup
        with open(backup_file, 'w') as f:
            subprocess.run(
                ["mysqldump", "-h", DB_HOST, "-u", DB_USER, f"-p{DB_PASS}", db_name],
                stdout=f,
                check=True
            )

        # Compacta o backup
        compressed_backup_file = f"{backup_file}.tar.gz"
        subprocess.run(["tar", "-czvf", compressed_backup_file, backup_file], check=True)
        os.remove(backup_file)  # Remove o arquivo SQL original

        # Envia para o Object Storage se sincronização estiver ativada
        if SYNC_WITH_OBJECT_STORAGE:
            s3_client.upload_file(compressed_backup_file, OBJECT_STORAGE_BUCKET, os.path.basename(compressed_backup_file))
            print(f"Backup realizado e enviado para o Object Storage com sucesso: {compressed_backup_file}")

def cleanup_local_backups():
    """Limpa os backups locais na pasta BACKUP_DIR."""
    print("Iniciando limpeza dos backups locais...")
    if SYNC_WITH_OBJECT_STORAGE:
        files = glob.glob(f"{BACKUP_DIR}/*.tar.gz")
        for file in files:
            os.remove(file)
            print(f"Backup local deletado: {file}")
        print("Limpeza total dos backups locais concluída.")
    else:
        files = glob.glob(f"{BACKUP_DIR}/*.tar.gz")
        file_times = [(file, os.path.getmtime(file)) for file in files]
        file_times.sort(key=lambda x: x[1], reverse=True)
        last_backup_files = [file for file, _ in file_times[:DAILY_RETENTION]]
        for file in files:
            if file not in last_backup_files:
                os.remove(file)
                print(f"Backup local deletado: {file}")
        print("Limpeza parcial dos backups locais concluída.")


def cleanup_old_backups():
    """Limpa backups antigos, mantendo backups a cada 15 minutos das últimas 24 horas e um backup diário dos últimos 7 dias."""
    cleanup_local_backups()  # Limpa os backups locais
    if SYNC_WITH_OBJECT_STORAGE:
        print("Iniciando limpeza dos backups antigos no Object Storage...")
        now = datetime.now()
        backups = s3_client.list_objects_v2(Bucket=OBJECT_STORAGE_BUCKET).get('Contents', [])
        
        for backup in backups:
            backup_time = datetime.strptime(backup['Key'].split('_')[-1].replace('.sql.gz', ''), "%Y-%m-%d_%H-%M-%S")
            # Backups mais antigos que 7 dias
            if backup_time < now - timedelta(hours=LAST_BACKUPS_RETENTION):
                s3_client.delete_object(Bucket=OBJECT_STORAGE_BUCKET, Key=backup['Key'])
                print(f"Backup deletado do Object Storage: {backup['Key']}")
            # Backups mais antigos que 24 horas mas dentro de 7 dias, manter um por dia
            elif backup_time < now - timedelta(days=1):
                daily_backup_time = backup_time.replace(hour=0, minute=0, second=0, microsecond=0)
                if (backup_time - daily_backup_time).total_seconds() >= 86400:  # Backups mais antigos que 24 horas
                    s3_client.delete_object(Bucket=OBJECT_STORAGE_BUCKET, Key=backup['Key'])
                    print(f"Backup deletado do Object Storage: {backup['Key']}. Bucket {OBJECT_STORAGE_BUCKET}")
        print(f"Limpeza dos backups antigos no Object Storage concluída. Bucket {OBJECT_STORAGE_BUCKET}")


logging.info("Realizando o primeiro backup...")
print("Realizando o primeiro backup...")

backup_mysql()

logging.info("Realizando Limpeza da pasta")
print("Realizando Limpeza da pasta")
cleanup_local_backups()
cleanup_old_backups()

# print("Agendando limpeza diária dos backups locais...")
# schedule.every().day.at("00:00").do(cleanup_local_backups)
# print("Agendamento de limpeza de backups locais concluído.")

# print(f"Agendando backups a cada {BACKUP_INTERVAL_MINUTES} minutos...")
# schedule.every(BACKUP_INTERVAL_MINUTES).minutes.do(backup_mysql)
# print("Agendamento de backups concluído.")

# print("Agendando limpeza diária dos backups...")
# schedule.every().day.at("00:00").do(cleanup_old_backups)
# print("Agendamento de limpeza concluído.")

print("Executando a programação...")
# while True:
#     schedule.run_pending()
#     time.sleep(1)
