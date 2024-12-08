# simulated-email-backend

Backend for an email service

Dependencies:

```txt
Django
daphne
django-cors-headers
channels
channels_redis
djangorestframework
psycopg2
pydantic
twilio
python-magic
python-magic-bin
Pillow
gunicorn
```

Requires `redis-server` for websocket: `redis-server.exe --port 6380`

Pre-loaded accounts in [stock_accounts.md](stock_accounts.md)
Login requires phone number and password
Register requires first, last name, phone number, email and password
Recover password requires **REAL** email and phone number
Change password requires **REAL** email
2FA requires **REAL** email
Phone verification (with twilio free trial) is limited to only verified callers

Project structure:

```txt
├─GotMail
│  └─__pycache__
├─gotmail_service
│  ├─migrations
│  │  └─__pycache__
│  ├─templates
│  │  └─registration
│  └─__pycache__
├─static
└─user_res
    └─profile_pictures
```

Example data is available in `dumped_data.json`, generated with `python GotMail\manage.py dumpdata > dumped_data.json`

To load, `python manage.py loaddata --exclude auth.permission --exclude contenttypes dumped_data.json`

Database:

```txt
Name: gotmailDB
Hostname: localhost
Port: 5432
Username: postgres
Password: 
Save password? [Check - on]
```

Edit the `super_secrets_py_template.txt > super_secrets.py` for secret variables

## Commands

Start Daphne

```cmd
daphne -b 0.0.0.0 -p $PORT GotMail.asgi:application
```

Start command

```cmd
python manage.py collectstatic --noinput && daphne -b 0.0.0.0 -p $PORT GotMail.asgi:application
```
