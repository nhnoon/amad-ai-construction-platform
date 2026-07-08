#!/usr/bin/env python
import os
import sys
import uvicorn

# Ensure backend directory is in path
sys.path.insert(0, os.path.dirname(__file__))

# Set environment variable
os.environ.setdefault('SESSION_SECRET', 'dev-secret')

if __name__ == '__main__':
    uvicorn.run(
        'app.main:app',
        host='127.0.0.1',
        port=8000,
        reload=False,
        log_level='info'
    )
