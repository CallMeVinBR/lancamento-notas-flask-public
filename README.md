# GradeSphere
Este projeto foi desenvolvido com o objetivo de aprimorar nossa competência e conhecimento em desenvolvimento de sistemas Web. Estamos felizes por compartilharmos nosso trabalho com você! This project was developed with the goal of enhancing our competence and knowledge in Web systems development. We're happy to share our work with you!

> [!NOTE]
> This project is not officially translated to English and the code was written in Brazilian Portuguese. Esse projeto não está oficialmente traduzido para Inglês e o código foi escrito em Português Brasileiro. Additionally, this project has a functionality of sending emails, so you won't be able to run it without properly setting up the Mailing service (Google Mail, for free).

## Como executar o projeto localmente
- Execute o seguinte comando em seu computador, para que possam ser baixadas as dependências necessárias para rodar o projeto:
  `pip install -r requirements.txt`
- Altere os dados da conexão do banco de dados MySQL em `services/config.py`;
- Configure seu arquivo .env conforme abaixo:
```
key=SUA_CHAVE_FLASK_APP
code=SEU_CODIGO_ACESSO_APP_EMAIL
mail=SEU_EMAIL_FONTE
server=smtp.googlemail.com
port=SUA_PORTA
db_host=SEU_HOST_BD
db_user=SEU_USUARIO_BD
db_pass=SUA_SENHA_BD
db_database=SEU_NOME_BANCO_DADOS
fernet_key=SUA_CHAVE_FERNET_GERADA
```
- Abra o diretório extraído do ZIP baixado no VS Code ou no editor de código que preferir;
- Execute o arquivo `app.py` e entre na URL retornada no prompt.

> [!WARNING]
> Certifique-se de executar as scripts SQL no diretório dumps.

## English version: How to run the project locally
- Run the following command in your machine, so that the required dependencies can be downloaded to run the project: `pip install -r requirements.txt`
- Change the MySQL connection data in `services/config.py`;
- Set up your .env file as shown below:
```
key=YOUR_FLASK_APP_KEY
code=YOUR_EMAIL_APP_ACCESS_CODE
mail=YOUR_EMAIL_SOURCE
server=smtp.googlemail.com
port=YOUR_PORT
db_host=YOUR_DATABASE_HOST
db_user=YOUR_DATABASE_USER
db_pass=YOUR_DATABASE_PASSWORD
db_database=YOUR_DATABASE_NAME
fernet_key=YOUR_GENERATED_FERNET_KEY
```
- Open the extracted directory from the downloaded ZIP file in VS Code or in your preferred code editor;
- Run the file `app.py` then click the returned URL in the prompt.

> [!WARNING]
> Make sure to run the SQL scripts in the dumps directory.
