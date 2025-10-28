#!/bin/bash

# 初始化数据库并导入数据
python database.py

# 启动 Streamlit
nohup streamlit run app.py --server.port 7863 > streamlit.log 2>&1 &