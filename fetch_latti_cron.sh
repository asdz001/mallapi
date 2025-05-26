#!/bin/bash

echo "🕒 $(date '+%Y-%m-%d %H:%M:%S') - 작업 시작" >> /root/fetch_latti_cron.log

source /root/venv/bin/activate
cd /root  
python3 manage.py fetch_and_register_latti


echo "✅ $(date '+%Y-%m-%d %H:%M:%S') - 작업 완료" >> /root/fetch_latti_cron.log
echo "------------------------------" >> /root/fetch_latti_cron.log


LOCKFILE="/tmp/fetch_latti.lock"

# 이미 실행 중이면 종료
if [ -f "$LOCKFILE" ]; then
  echo "🛑 작업이 이미 실행 중입니다." >> /root/fetch_latti_cron.log
  exit 1
fi

# 락 생성
touch "$LOCKFILE"

# 가상환경 진입 및 실행
source /root/venv/bin/activate
cd /root
python3 manage.py fetch_and_register_latti

# 락 해제
rm -f "$LOCKFILE"