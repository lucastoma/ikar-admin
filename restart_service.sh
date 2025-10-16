#!/bin/bash

# Restart usługi ikar-admin z symlinkiem
echo "Restartuję usługę ikar-admin..."

# Zatrzymaj usługę
sudo systemctl stop ikar-admin.service

# Odśwież symlink (nadpisze istniejący bez pytania)
sudo ln -sf /workspace/ikar_apps/ikar-admin/systemd/ikar-admin.service /etc/systemd/system/

# Przeładuj daemony
sudo systemctl daemon-reload

# Uruchom usługę
sudo systemctl start ikar-admin.service

# Pokaż status
echo "Status po restarcie:"
sudo systemctl status ikar-admin.service --no-pager

echo "Usługa ikar-admin została zrestartowana z aktualnym symlinkiem."