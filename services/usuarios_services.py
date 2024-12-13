import datetime
from services import config

def deletar_nao_verificado():
    db = config.conectar()
    cursor = db.cursor(prepared=True)
    um_mes_atras = datetime.datetime.now().date() - datetime.timedelta(days=30)
    cursor.execute("DELETE FROM usuarios WHERE (ultimo_login < %s AND auth = 0)", (um_mes_atras,))
    db.commit()
    cursor.close()
    
def deletar_inativo():
    db = config.conectar()
    cursor = db.cursor(prepared=True)
    seis_meses_atras = datetime.datetime.now().date() - datetime.timedelta(days=180)
    cursor.execute("DELETE FROM usuarios WHERE ultimo_login < %s", (seis_meses_atras,))
    db.commit()
    cursor.close()
    
def deletar_req_alt_senha():
    db = config.conectar()
    cursor = db.cursor(prepared=True)
    um_dia_atras = datetime.datetime.now().date() - datetime.timedelta(days=1)
    cursor.execute("DELETE FROM alt_senha WHERE dia_solic < %s", (um_dia_atras,))
    db.commit()
    cursor.close()
    
def deletar_convites():
    db = config.conectar()
    cursor = db.cursor(prepared=True)
    duas_semanas_atras = datetime.datetime.now().date() - datetime.timedelta(days=14)
    cursor.execute("DELETE FROM turmas_convites WHERE criado_em = %s", (duas_semanas_atras,))
    db.commit()
    cursor.close()