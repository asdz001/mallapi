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
