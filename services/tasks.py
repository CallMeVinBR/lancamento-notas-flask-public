from apscheduler.schedulers.background import BackgroundScheduler
from services.usuarios_services import deletar_nao_verificado, deletar_inativo, deletar_req_alt_senha, deletar_convites

scheduler = BackgroundScheduler()
scheduler.add_job(deletar_nao_verificado, 'cron', hour=0, minute=0)
scheduler.add_job(deletar_inativo, 'cron', hour=1, minute=0)
scheduler.add_job(deletar_req_alt_senha, 'cron', hour=2, minute=0)
scheduler.add_job(deletar_convites, 'cron', hour=3, minute=0)