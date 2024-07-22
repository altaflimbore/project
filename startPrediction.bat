@echo off
setlocal
streamlit run prediction.py --server.port 9000 --server.headless true
