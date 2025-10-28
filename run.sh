#!/bin/bash

# 初始化数据库并导入数据
python3 database.py

# 启动 Streamlit
streamlit run app.py
