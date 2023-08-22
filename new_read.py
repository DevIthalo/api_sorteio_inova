from flask import Flask, Response
import os.path
import os
import random
import json
import psycopg2
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from flask_cors import CORS 
from flask import request

app = Flask(__name__)
CORS(app)  

# Configurações de conexão com o banco de dados
DB_CONFIG = {
    'host': 'silly.db.elephantsql.com',
    'port': 5432,
    'database': 'duqsjqfq',
    'user': 'duqsjqfq',
    'password': 'ReZc8xedWGBNyC6sq915giOfNBUdTsSq'
}

# Restante das importações...
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

SAMPLE_SPREADSHEET_ID = '1h-IYaShYgfEkruekbnJFtGQGj495d_45sRCb9G73QV4'
SAMPLE_RANGE_NAME = 'Respostas ao formulário 1!C2:G459'


# Função para armazenar o token no banco de dados
def store_token_in_db(token):
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
       
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS token_storage (
            id SERIAL PRIMARY KEY,
            token JSONB
        )
    ''')
       
    cursor.execute('''
        INSERT INTO token_storage (token)
        VALUES (%s)
        RETURNING id
    ''', (json.dumps(token),))
       
    conn.commit()
    conn.close()


# Função para obter as credenciais do banco de dados
def get_db_credentials():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    cursor.execute('SELECT token FROM token_storage ORDER BY id DESC LIMIT 1')
    token = cursor.fetchone()
    
    conn.close()
    
    if token:
        return json.loads(token[0])
    else:
        return None
    


def get_random_row(valor_pesquisa):
    creds = get_db_credentials()

    if not creds:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
        store_token_in_db(creds.to_json())  # Armazena o novo token no banco de dados

    creds = Credentials.from_authorized_user_info(creds)  # Converte o dicionário em objeto Credentials

    if not creds.valid:
        creds.refresh(Request())

    try:
        service = build('sheets', 'v4', credentials=creds)
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                    range=SAMPLE_RANGE_NAME).execute()
        values = result.get('values', [])
        if not values:
            return None

        for row in values:
            if int(row[4]) == valor_pesquisa:
                return {
                    'vendedor': row[0],
                    'cliente': row[1],
                    'telefone': row[2], 
                    'ponto': row[4],
                }

        return None

    except HttpError as err:
        print(err)
        return None




@app.route('/', methods=['GET', 'POST'])
def index():
    request_data = request.json

    random_data = get_random_row(request_data['result'])
    if random_data:
        json_data = json.dumps(random_data, ensure_ascii=False)
        response = Response(json_data, content_type='application/json;')
        return response
    else:
        error_response = {"error": "O ponto sorteado não possui registro de venda."}
        return Response(json.dumps(error_response), content_type='application/json')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)

