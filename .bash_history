apt-get upgrade
apt autoremove
apt-get upgrade
uname -a
dpkg -l | grep fail2ban
dpkg -l | grep gcc
dpkg -l | grep openssl
systemctl stop fail2ban.service
systemctl disable fail2ban.service
systemctl list-unit-files | grep enabled
cat /etc/resolv.conf
ll
> .bash_history 
shutdown -h now
vi /etc/networks 
vi /etc/network/interfaces
shutdown -h now
vi /etc/network/interfaces
service networking restart
vi /etc/network/interfaces
service networking restart
shutdown -h now
vi /etc/ssh/sshd_config
service sshd restart
uanem -r
uname -r
cd /etc/network
ll
cp -a interfaces interfaces_org
vi interfaces
reboot
uname -a
uname -r
apt-cache search linux-image-5 |grep "generic"
apt-cache search linux-image-5 |grep "5.15."
apt-cache search linux-image-5 |grep "5.15.0"
apt-get update
apt-cache search linux-image-5 |grep "generic"
apt-cache search linux-image-5 |grep "generic" |grep 52
apt-get install linux-image-5.15.0-52-generic
reboot
uanme -r
uname -r
cd /etc/network
ll
mv interfaces_org interfaces
reboot
uptime
uname -r
ifconfig

apt update && apt install -y python3 python3-pip python3-venv unzip
unzip mallapi.zip
cd mallapi
[200~unzip mallapi.Zip
cd mallap~
apt update && apt install -y unzip
unzip mallapi.Zip
cd mallapi
ls
[200~rm -rf ~/.vscode-server~
rm -rf ~/.vscode-server
apt update && apt install -y zip unzip
mkdir /home/mallapi
cp -r /root/mallapi/* /home/mallapi/
venv/bin/activate
cd ~/mallapi
venv/bin/activate 
venv/bin/activate
source venv/bin/activate
cd ~/mallapi
source ../venv/bin/activate
cd ~/mallapi
source ../venv/bin/activate
cd ~
source venv/bin/activate
cd ~              # 홈 디렉토리로 이동
source venv/bin/activate   # 가상환경 활성화
cd ~
source venv/bin/activate
cd mallapi
python3 manage.py runserver 0.0.0.0:8000
source venv/bin/activate
source venv/bin/activate
cd mallapi
source venv/bin/activate
venv\Scripts\activate
source mallapi/venv/bin/activate
source venv/bin/activate
cd ~/mallapi
rm -rf venv                # 기존 Windows용 venv 삭제
python3 -m venv venv       # Linux에서 새로 venv 생성
source venv/bin/activate   # 가상환경 진입
rm -rf venv 
pip install --upgrade pip
pip install django
python manage.py --version
python3 manage.py --version
venv/bin/python manage.py --version
cd ~
source venv/bin/activate
python3 manage.py runserver 0.0.0.0:8000
pip install django-multiselectfield
python3 manage.py runserver 0.0.0.0:8000
pip install pandas
python3 manage.py runserver 0.0.0.0:8000
source ~/venv/bin/activate
pip install django
pip install gunicorn
gunicorn --bind 0.0.0.0:8000 mallapi.wsgi:application
Gunicorn
sudo apt update
sudo apt install -y nginx
sudo systemctl start nginx
sudo ln -s /etc/nginx/sites-available/mallapi /etc/nginx/sites-enabled
sudo nginx -t    # 설정 테스트
sudo systemctl restart nginx
ps aux | grep gunicorn
gunicorn mallapi.wsgi:application --bind 127.0.0.1:8000 --chdir /root
cd ~/mallapi
source ~/venv/bin/activate
python3 manage.py collectstatic
cd ~
source venv/bin/activate
python3 manage.py collectstatic
cd ~
source venv/bin/activate
python3 manage.py collectstatic
location /static/ {
}
source /root/venv/bin/activate
python3 -m venv venv
source ~/venv/bin/activate
python3 manage.py runserver 0.0.0.0:8000
pip install django-multiselectfield
python3 manage.py runserver 0.0.0.0:8000
ModuleNotFoundError: No module named 'pandas'
python3 manage.py runserver 0.0.0.0:8000
pip install pandas
python3 manage.py runserver 0.0.0.0:8000
sudo apt update
sudo apt install nginx -y
sudo systemctl status nginx
sudo nano /etc/nginx/sites-available/mallapi
sudo ln -s /etc/nginx/sites-available/mallapi /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
sudo ln -s /etc/nginx/sites-available/mallapi /etc/nginx/sites-enabled/
sudo nano /etc/systemd/system/gunicorn.service
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable gunicorn
sudo systemctl start gunicorn
sudo systemctl status gunicorn
/bin/python2 /root/.vscode-server/extensions/ms-python.python-2025.6.1-linux-x64/python_files/printEnvVariablesToFile.py /root/.vscode-server/extensions/ms-python.python-2025.6.1-linux-x64/python_files/deactivate/bash/envVars.txt
sudo nano /etc/nginx/sites-available/mallapi
sudo nginx -t                     # 설정 확인
sudo systemctl reload nginx       # 설정 반영 (restart보다 안전)
python3 manage.py collectstatic
sudo nginx -t              # 설정 확인
sudo systemctl reload nginx
sudo chmod -R 755 /root/staticfiles
sudo find /root/staticfiles -type f -exec chmod 644 {} \;
ps -ef | grep nginx
sudo chmod -R 755 /root/staticfiles
sudo chown -R www-data:www-data /root/staticfiles
sudo nginx -t
sudo systemctl restart nginx
sudo mkdir -p /var/www/staticfiles
python3 manage.py collectstatic --noinput
sudo mv /root/staticfiles/* /var/www/staticfiles/
sudo nano /etc/nginx/sites-available/mallapi
sudo nginx -t
sudo systemctl reload nginx
git init
git add .
sudo apt update && sudo apt install git -y
git --version
git init
git add .
git commit -m "first commit"
git remote add origin https://github.com/asdz001/mallapi.git
git branch -M main
git push -u origin main
ssh-keygen -t rsa -b 4096 -C "github_deploy"
cat ~/.ssh/id_rsa
cat ~/.ssh/id_rsa.pub
nano ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh
git add .gitignore
git commit -m "🧹 .gitignore 추가 및 불필요 파일 무시 설정"
git push origin main
git add .gitignore
git commit -m "🧹 .gitignore 추가 및 불필요 파일 무시 설정"
git push origin main
/usr/bin/python2 /root/.vscode-server/extensions/ms-python.python-2025.6.1-linux-x64/python_files/printEnvVariablesToFile.py /root/.vscode-server/extensions/ms-python.python-2025.6.1-linux-x64/python_files/deactivate/bash/envVars.txt
python manage.py showmigrations
python3 manage.py showmigrations
python manage.py shell
python3 manage.py shell
python3 manage.py showmigrations
python3 manage.py migrate
python3 manage.py shell
ls -l db.sqlite3
python3 manage.py shell
python3 manage.py createsuperuser
/bin/python2 /root/.vscode-server/extensions/ms-python.python-2025.6.1-linux-x64/python_files/printEnvVariablesToFile.py /root/.vscode-server/extensions/ms-python.python-2025.6.1-linux-x64/python_files/deactivate/bash/envVars.txt
python3 manage.py shell
python3 manage.py fetch_and_register_latti
pip install requests
python3 manage.py fetch_and_register_latti
python3 manage.py shell
python3 manage.py makemigrations eventlog
python3 manage.py migrate eventlog
python3 manage.py fetch_and_register_latti
sudo systemctl restart gunicorn
sudo systemctl restart nginx
sudo systemctl status gunicorn
cd /home/ubuntu/mallapi
source venv/bin/activate
gunicorn mallapi.wsgi:application
sudo systemctl restart gunicorn
sudo systemctl restart nginx
nano /root/fetch_latti_cron.sh
chmod +x /root/fetch_latti_cron.sh
crontab -e
crontab -l
bash /root/fetch_latti_cron.sh
crontab -e
crontab -l
crontab -e
crontab -l
/usr/bin/python2 /root/.vscode-server/extensions/ms-python.python-2025.6.1-linux-x64/python_files/printEnvVariablesToFile.py /root/.vscode-server/extensions/ms-python.python-2025.6.1-linux-x64/python_files/deactivate/bash/envVars.txt
python manage.py shell
python3 manage.py shell
python3 manage.py fetch_and_register_latti
which python
which pip
/root/venv/bin/activate
source /root/venv/bin/activate
python3 manage.py fetch_and_register_latti
python3 manage.py showmigrations
python3 manage.py shell
python3 manage.py fetch_and_register_latti
proxy_read_timeout 300;
proxy_connect_timeout 300;
proxy_send_timeout 300;
sudo nano /etc/nginx/sites-available/default
sudo nano /etc/systemd/system/gunicorn.service
sudo nano /etc/nginx/sites-available/default
sudo nginx -t                  # 설정 확인
sudo systemctl reload nginx    # 설정 적용
sudo nano /etc/nginx/sites-available/default
sudo nginx -t               # ✅ 설정 확인 (정상일 때 "syntax is ok")
sudo systemctl reload nginx # ✅ 설정 적용
sudo nano /etc/nginx/sites-available/default
sudo nginx -t
sudo systemctl reload nginx
sudo systemctl restart gunicorn
sudo systemctl status gunicorn
python3 manage.py runserver 0.0.0.0:8000
lsof db.sqlite3
sudo systemctl stop gunicorn
kill -9 40848 42806 43277 49801
lsof db.sqlite3
python3 manage.py runserver 0.0.0.0:8000
supervisorctl restart gunicorn
sudo systemctl restart gunicorn
sudo systemctl restart nginx
sudo systemctl restart gunicorn
sudo systemctl restart nginx
sudo systemctl restart gunicorn
sudo systemctl restart nginx
python3 manage.py fetch_and_register_latti
python3 shop/services/product/conversion_service.py
PYTHONPATH=. python3 shop/services/product/conversion_service.py
PYTHONPATH=. python3 shop/scripts/run_conversion.py
python3 manage.py fetch_and_register_latti
sudo systemctl restart gunicorn
sudo systemctl restart nginx
python manage.py shell
sudo systemctl restart gunicorn
sudo systemctl restart nginx
python manage.py shell
sudo systemctl restart gunicorn
sudo systemctl restart nginx
python manage.py shell
python3 manage.py shell
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo -u postgres psql
ls -l /usr/bin/psql
ls -l /usr/share/postgresql-common/pg_wrapper
sudo -u postgres psql
ls -l /usr/share/postgresql-common/pg_wrapper
sudo chmod +x /usr/share/postgresql-common/pg_wrapper
sudo chmod +x /usr/bin/psql
sudo -u postgres psql
sudo su - postgres
psql
sudo chmod 755 /usr/bin/perl
sudo -u postgres psql
python manage.py migrate
pip install psycopg2-binary
python manage.py migrate
# 루트 디렉터리에서 실행
python manage.py dumpdata --exclude auth.permission --exclude contenttypes > db_backup.json
python manage.py showmigrations
python manage.py loaddata db_backup.json
cat db_backup.json | head -n 20
ls -lh db_backup.json
python manage.py dumpdata --exclude auth.permission --exclude contenttypes > db_backup.json
cat db_backup.json | head -n 10
ls -lh db_backup.json
python manage.py migrate
python manage.py loaddata db_backup.json
python manage.py shell
sudo -u postgres psql
python manage.py loaddata db_backup.json
jobs
fg %11
python manage.py flush
python manage.py dumpdata --exclude auth.permission --exclude contenttypes --exclude admin.logentry > db_backup.json
python manage.py loaddata db_backup.json
sudo systemctl restart gunicorn
sudo systemctl restart nginx
crontab -l
mkdir -p /root/static
python manage.py collectstatic
sudo systemctl restart gunicorn
python3 manage.py migrate
sudo systemctl daemon-reload
sudo systemctl restart gunicorn
venv\Scripts\activate
cat ~/.bashrc | grep activate
deactivate
/usr/bin/python2 /root/.vscode-server/extensions/ms-python.python-2025.6.1-linux-x64/python_files/printEnvVariablesToFile.py /root/.vscode-server/extensions/ms-python.python-2025.6.1-linux-x64/python_files/deactivate/bash/envVars.txt
source /root/venv/bin/activate
pip install openpyxl
df -h
source venv/bin/activate
git pull origin main
(Gunicorn 재시작) - 코드 수정하면 작업해야함
sudo systemctl restart gunicorn
git pull origin main
(Gunicorn 재시작) - 코드 수정하면 작업해야함
sudo systemctl restart gunicorn
git pull origin main
git reset --hard
git pull origin main
crontab -e
python manage.py fetch_and_register_cuccuini
sudo systemctl restart gunicorn
git pull origin main
(Gunicorn 재시작) - 코드 수정하면 작업해야함
sudo systemctl restart gunicorn
/bin/python2 /root/.vscode-server/extensions/ms-python.python-2025.6.1-linux-x64/python_files/printEnvVariablesToFile.py /root/.vscode-server/extensions/ms-python.python-2025.6.1-linux-x64/python_files/deactivate/bash/envVars.txt
/usr/bin/python2 /root/.vscode-server/extensions/ms-python.python-2025.6.1-linux-x64/python_files/printEnvVariablesToFile.py /root/.vscode-server/extensions/ms-python.python-2025.6.1-linux-x64/python_files/deactivate/bash/envVars.txt
/bin/python2 /root/.vscode-server/extensions/ms-python.python-2025.6.1-linux-x64/python_files/printEnvVariablesToFile.py /root/.vscode-server/extensions/ms-python.python-2025.6.1-linux-x64/python_files/deactivate/bash/envVars.txt
source venv/bin/activate
python manage.py fetch_and_register_all
source venv/bin/activate
crontab -l
git fetch origin
git reset --hard origin/main
python manage.py shell
python manage.py fetch_and_register_baseblu
python manage.py shell
/usr/bin/python2 /root/.vscode-server/extensions/ms-python.python-2025.6.1-linux-x64/python_files/printEnvVariablesToFile.py /root/.vscode-server/extensions/ms-python.python-2025.6.1-linux-x64/python_files/deactivate/bash/envVars.txt
source venv/bin/activate
crontab -l
python manage.py fetch_and_register_gaudenzi
python manage.py makemigrations
python manage.py migrate
crontab -l
/bin/python2 /root/.vscode-server/extensions/ms-python.python-2025.8.0-linux-x64/python_files/printEnvVariablesToFile.py /root/.vscode-server/extensions/ms-python.python-2025.8.0-linux-x64/python_files/deactivate/bash/envVars.txt
source venv/bin/activate
crontab -e
crontab -l
python manage.py makemigrations
python manage.py migrate
sudo systemctl restart gunicorn
python manage.py makemigrations
python manage.py migrate
sudo systemctl restart gunicorn
git pull origin main
python manage.py collectstatic --noinput
python manage.py collectstatic
sudo systemctl restart gunicorn
cat /root/staticfiles/shop/admin_cart.js | grep saveAllCartOptions
python manage.py collectstatic --noinput
cat /root/staticfiles/shop/admin_cart.js | grep saveAllCartOptions
python manage.py makemigrations
python manage.py migrate
sudo systemctl restart gunicorn
코드 변경시 반영(재시작) - html일경우
sudo systemctl restart gunicorn
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py makemigrations
python manage.py migrate
sudo systemctl restart gunicorn
코드 변경시 반영(재시작) - html일경우
sudo systemctl restart gunicorn
python manage.py collectstatic --noinput
rm -rf /root/staticfiles/
python manage.py collectstatic --noinput
rm -rf /root/staticfiles/
python manage.py collectstatic --noinput
python manage.py makemigrations
python manage.py migrate
sudo systemctl restart gunicorn
코드 변경시 반영(재시작) - html일경우
sudo systemctl restart gunicorn
python manage.py collectstatic --noinput
rm -rf /root/staticfiles/
python manage.py collectstatic --noinput
rm -rf /root/staticfiles/
rm staticfiles.json
rm -rf staticfiles/
python manage.py collectstatic --noinput
ls staticfiles/shop/
python manage.py shell
python manage.py collectstatic --noinput --verbosity 2
cd static/shop
cp admin_cart.js admin_cart_temp.js
rm admin_cart.js
mv admin_cart_temp.js admin_cart.js
cd ~/mallapi/static/shop
cp admin_cart.js admin_cart_temp.js
rm admin_cart.js
mv admin_cart_temp.js admin_cart.js
find . -name admin_cart.js
cd shop/static/shop
cp admin_cart.js admin_cart_temp.js
rm admin_cart.js
mv admin_cart_temp.js admin_cart.js
cd shop/static/shop
python manage.py collectstatic --noinput --verbosity 2
cd ~/mallapi
python manage.py collectstatic --noinput --verbosity 2
find /root -name manage.py
cd /root
python manage.py collectstatic --noinput --verbosity 2
ls staticfiles/shop/
cd /root/mallapi/shop/static/shop
mkdir -p /root/static/shop
cp admin_cart.js /root/static/shop/
cd /root/shop/static/shop
cp admin_cart.js /root/static/shop/
ls /root/static/shop/
cd /root
python manage.py collectstatic --noinput --verbosity 2
ls /root/staticfiles/shop/
rm /root/mallapi/shop/static/shop/admin_cart.js
find /root -name admin_cart.js
rm /root/shop/static/shop/admin_cart.js
python manage.py collectstatic --noinput --verbosity 2
ls /root/staticfiles/shop/
python manage.py collectstatic --noinput --verbosity 2
ls /root/staticfiles/shop/
mv /root/static/shop/admin_cart.js /root/static/shop/admin_cart.v2.js
python manage.py collectstatic --noinput
python manage.py makemigrations
python manage.py migrate
sudo systemctl restart gunicorn
코드 변경시 반영(재시작) - html일경우
sudo systemctl restart gunicorn
ls /root/static/shop/
ps aux | grep nginx
sudo nano /etc/nginx/sites-available/default
sudo systemctl restart nginx
sudo nginx -T | grep static
sudo nano /etc/nginx/sites-available/default
sudo nginx -t  # ✅ 문법 체크
sudo systemctl reload nginx  # ✅ 설정 반영
python manage.py collectstatic --noinput
cd ~/mallapi  # mallapi 프로젝트 디렉토리로 이동
git reset --hard origin/main
python manage.py collectstatic --noinput
python manage.py makemigrations
python manage.py migrate
cd /root
python manage.py makemigrations
python manage.py migrate
sudo systemctl restart gunicorn
코드 변경시 반영(재시작) - html일경우
sudo systemctl restart gunicorn
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic --noinput
ls -al /root/staticfiles/shop/admin_cart.* 
python manage.py collectstatic
sudo systemctl restart gunicorn
코드 변경시 반영(재시작) - html일경우
sudo systemctl restart gunicorn
python manage.py collectstatic
git pull origin main
python manage.py collectstatic
python manage.py collectstatic --clear --noinput
ls -al /root/staticfiles/shop/admin_cart.js
cat /root/staticfiles/shop/admin_cart.js | tail -n 20
git pull origin main
python manage.py collectstatic --clear --noinput
cat /root/staticfiles/shop/admin_cart.js | tail -n 20
git reset --hard HEAD
git pull origin main
python manage.py collectstatic --clear --noinput
cat /root/staticfiles/shop/admin_cart.js | tail -n 20
cat /etc/nginx/sites-enabled/default
cat /etc/nginx/nginx.conf
sudo nginx -T | grep static
sudo nano /etc/nginx/sites-enabled/default
sudo nginx -T | grep -A 5 "location /static/"
sudo nginx -T | grep -B 10 "alias /var/www/staticfiles"
sudo nano /etc/nginx/sites-enabled/mallapi
sudo nginx -t
sudo systemctl reload nginx
sudo nano /etc/nginx/sites-enabled/mallapi
sudo nginx -t
sudo nano /etc/nginx/sites-enabled/mallapi
sudo nginx -t
sudo systemctl reload nginx
python manage.py makemigrations
python manage.py migrate
sudo nano /etc/nginx/sites-enabled/mallapi
sudo nginx -t
sudo systemctl reload nginx
git fetch origin
git reset --hard origin/main
python manage.py collectstatic --clear --noinput
sudo rm -rf /root/staticfiles
crontab -l
crontab -e
python manage.py fetch_and_register-eleonorabonucci' >> /root/test_scheduler.log 2>&1


python manage.py fetch_and_register-eleonorabonucci
python manage.py fetch_and_register_eleonorabonucci
sudo nginx -T | grep -A 5 "location /static/"
python manage.py makemigrations myshop
python manage.py migrate myshop
sudo systemctl reload nginx
python manage.py collectstatic --clear --noinput
sudo systemctl reload nginx
sudo nginx -t
sudo systemctl reload nginx
python manage.py collectstatic --clear --noinput
sudo systemctl reload nginx
python manage.py collectstatic --clear --noinput
sudo systemctl reload nginx
python manage.py collectstatic --clear --noinput
sudo systemctl reload nginx
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic --clear --noinput
class Media:
ls -al /var/www/staticfiles/shop/admin_cart.js
python manage.py shell
sudo rm -rf /root/staticfiles
python manage.py collectstatic --clear --noinput
tail -n 100 /var/log/nginx/access.log | grep admin_cart.js
python manage.py shell
sudo systemctl restart gunicorn
python manage.py fetch_and_register_baseblu
/bin/python2 /root/.vscode-server/extensions/ms-python.python-2025.8.0-linux-x64/python_files/printEnvVariablesToFile.py /root/.vscode-server/extensions/ms-python.python-2025.8.0-linux-x64/python_files/deactivate/bash/envVars.txt
source venv/bin/activate
python manage.py fetch_and_register_baseblu
source venv/bin/activate
python manage.py fetch_and_register_cuccuini
sudo systemctl restart gunicorn
python manage.py shell
/bin/python2 /root/.vscode-server/extensions/ms-python.python-2025.8.0-linux-x64/python_files/printEnvVariablesToFile.py /root/.vscode-server/extensions/ms-python.python-2025.8.0-linux-x64/python_files/deactivate/bash/envVars.txt
source venv/bin/activate
git add -A
git commit -m "🔁 장바구니 및 아뜰리에 주문 수정 "
git push origin main
crontab -l
sudo systemctl restart gunicorn
git fetch origin
git reset --hard origin/main
sudo systemctl restart gunicorn
python manage.py fetch_and_register_eleonorabonucci
crontab -e
crontab -l
sudo systemctl restart gunicorn
python /root/.vscode-server/extensions/ms-python.python-2025.8.0-linux-x64/python_files/printEnvVariablesToFile.py /root/.vscode-server/extensions/ms-python.python-2025.8.0-linux-x64/python_files/deactivate/bash/envVars.txt
source venv/bin/activate
python shop/api/atelier/test_single_product.py
/usr/bin/python2 /root/.vscode-server/extensions/ms-python.python-2025.8.0-linux-x64/python_files/printEnvVariablesToFile.py /root/.vscode-server/extensions/ms-python.python-2025.8.0-linux-x64/python_files/deactivate/bash/envVars.txt
