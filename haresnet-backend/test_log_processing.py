import os
import time
from app import create_app, db
from app.models import DNSQueryLog

def append_logs():
    log_file = '/var/log/dnsmasq.log'
    timestamp = time.strftime('%b %d %H:%M:%S')
    
    entries = [
        f'{timestamp} dnsmasq[123]: query[A] google.com from 192.168.1.100',
        f'{timestamp} dnsmasq[123]: query[AAAA] facebook.com from 192.168.1.101',
        f'{timestamp} dnsmasq[123]: query[A] doubleclick.net from 192.168.1.102'
    ]
    
    print(f"Appending {len(entries)} log entries to {log_file}...")
    with open(log_file, 'a') as f:
        for entry in entries:
            f.write(entry + '\n')
            
def check_db():
    app = create_app()
    with app.app_context():
        count = DNSQueryLog.query.count()
        print(f"Database now has {count} DNS query logs.")
        if count > 0:
            last_log = DNSQueryLog.query.order_by(DNSQueryLog.id.desc()).first()
            print(f"Last log: {last_log.to_dict()}")

if __name__ == "__main__":
    if not os.path.exists('/var/log/dnsmasq.log'):
        print("Creating /var/log/dnsmasq.log")
        open('/var/log/dnsmasq.log', 'w').close()
        
    append_logs()
    print("Waiting 10 seconds for parser to pick up logs...")
    time.sleep(10)
    check_db()
