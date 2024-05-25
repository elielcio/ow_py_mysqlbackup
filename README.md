# Backup Automático de MySQL para Object Storage

Este é um script Python que realiza backups automáticos dos bancos de dados MySQL locais e os envia para um serviço de armazenamento de objetos (Object Storage) utilizando a biblioteca `boto3`.

## Instalação

### 1. Preparação do Ambiente

Certifique-se de ter o Python 3 e o pip instalados no seu sistema. Você também precisará do cliente MySQL instalado para a comunicação com o servidor MySQL local.

```bash
sudo apt update
sudo apt install python3 python3-pip mysql-client
```

### 2. Configuração do Projeto

Clone este repositório:

```bash
git clone https://github.com/seu_usuario/ow_py_mysqlbackup.git
cd ow_py_mysqlbackup
```

### 3. Configuração do Ambiente Virtual
Crie e ative um ambiente virtual para isolar as dependências do projeto:

```bash

python3 -m venv ow_py_mysqlbackupenv
source ow_py_mysqlbackupenv/bin/activate
```

Instale as dependências do projeto:

```bash
Copiar código
pip install -r requirements.txt
```

### 4. Configuração do Script
Edite o arquivo backup_mysql.py com as configurações corretas para o MySQL e o Object Storage. Você precisará fornecer as informações de conexão do seu MySQL local e as credenciais de acesso ao Object Storage.

```python
Copiar código
# Configurações
DB_HOST = "localhost"
DB_USER = "seu_usuario"
DB_PASS = "sua_senha"
BACKUP_DIR = "/home/ow_py_mysqlbackup/backups"
OBJECT_STORAGE_BUCKET = "ow-bk-db-01"
OBJECT_STORAGE_URL = "https://usc1.contabostorage.com/ow-bk-db-01"
AWS_ACCESS_KEY = "seu_access_key"
AWS_SECRET_KEY = "seu_secret_key"
```

### 5. Execução do Script
Você pode executar o script manualmente para testar:

```bash
Copiar código
python3 src/backup_mysql.py
```

O script será executado e realizará backups dos bancos de dados MySQL locais.

Execução Automática
Para executar o script automaticamente em intervalos regulares, você pode usar o serviço systemd ou o cron.

Utilizando Systemd
Você pode criar um serviço systemd para iniciar e gerenciar o script. Veja as instruções detalhadas aqui.

Utilizando Cron
Você pode agendar a execução do script usando o cron. Veja as instruções detalhadas aqui.

Observações
Certifique-se de substituir todos os valores de configuração padrão no script pelas suas próprias informações de configuração antes de executá-lo.

csharp
Copiar código

Este arquivo README fornece uma visão geral clara dos passos necessários pa