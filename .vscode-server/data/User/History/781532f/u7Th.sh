#!/bin/bash
source /root/venv/bin/activate
cd /root/mallapi  # ← 여기를 실제 manage.py 위치로 바꾸세요!
python3 manage.py fetch_and_register_latti
