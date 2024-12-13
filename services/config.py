import mysql.connector
from dotenv import load_dotenv
import os

load_dotenv('../.env')

def conectar():
    return mysql.connector.connect(
        host=os.getenv('db_host'),
        user=os.getenv('db_user'),
        password=os.getenv('db_pass'),
        database=os.getenv('db_database')
    )
