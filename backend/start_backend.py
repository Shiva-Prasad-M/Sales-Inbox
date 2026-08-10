import os
from uvicorn import run

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

if __name__ == '__main__':
    run('app.main:app', host='127.0.0.1', port=8002, log_level='info')
