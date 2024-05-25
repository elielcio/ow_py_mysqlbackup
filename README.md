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

### 4. Configuração do Arquivo de Configuração
Antes de executar o script, é necessário configurar o arquivo de configuração. Siga as instruções abaixo:

No diretório do projeto, localize o arquivo config-example.ini.
Faça uma cópia deste arquivo e renomeie-a para config.ini.
Edite o arquivo config.ini com suas próprias configurações do MySQL e Object Storage.
Por exemplo:

bash
Copiar código
cp config-example.ini config.ini
Isso irá criar uma cópia do arquivo de exemplo como config.ini, que você pode então editar com suas configurações específicas.

Edite o arquivo backup_mysql.py com as configurações corretas para o MySQL e o Object Storage. Você precisará fornecer as informações de conexão do seu MySQL local e as credenciais de acesso ao Object Storage.


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