import uvicorn
import os

def start_server():

    uvicorn.run(
        app='app:app',
        host='0.0.0.0',
        port=8001,
        reload=True,
    )

if __name__ == '__main__':
    start_server()