import os
import sys
import subprocess

# Načtení a ověření základních environment proměnných pro DB
required_env_vars = [
    'ABK_SSL' # povoli/zakaze SSL na ABK serveru (bere hodnoty true/false)
    #'ABK_PORT' # port na kterem addressbook pobezi
]

missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    print(f"Chybi nasledujici environment promenne: {', '.join(missing_vars)}")
    sys.exit(1)

use_ssl = os.getenv('ABK_SSL', 'true').lower() in ['1', 'true', 'yes']
if use_ssl:
    if not os.getenv('ABK_HOSTNAME'): # pokud je zapnuto SSL, kontroluje se pritomnost promenne ABK_HOSTNAME
        print(f"Pro fungovani SSL je vyzadovana enviroment promenna ABK_HOSTNAME")
        sys.exit(1)

api_hostname = os.getenv('ABK_HOSTNAME')
api_port = os.getenv('ABK_PORT', '5000')

# SSL certifikáty
ssl_cert = 'ssl/cert.pem'
ssl_key = 'ssl/key.pem'


def generate_self_signed_cert():
    print("Generuji self-signed SSL certifikat...")
    subprocess.run([
        'openssl', 'req', '-x509', '-nodes', '-days', '365',
        '-newkey', 'rsa:2048',
        '-keyout', ssl_key,
        '-out', ssl_cert,
        '-subj', f'/CN={api_hostname}'
    ], check=True)


def ensure_ssl_certificates():
    if not os.path.exists(ssl_cert) or not os.path.exists(ssl_key):
        print("Nebyl nalezen SSL certifikat")
        generate_self_signed_cert()


if __name__ == '__main__':
    if use_ssl:
        ensure_ssl_certificates()
        subprocess.run([
            'gunicorn', '-w', '4', '-b', f'0.0.0.0:{api_port}',
            '--certfile=ssl/cert.pem',
            '--keyfile=ssl/key.pem',
            'abk:app'
        ], check=True)

    else:
        subprocess.run([
            'gunicorn', '-w', '4', '-b', f'0.0.0.0:{api_port}',
            'abk:app'
        ], check=True)
    