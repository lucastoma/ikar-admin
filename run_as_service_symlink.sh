#!/bin/bash

# Zatrzymaj usługę
sudo systemctl stop ikar-admin.service

# Utwórz symlink (nadpisze istniejący bez pytania)
sudo ln -sf /workspace/ikar_apps/ikar-admin/systemd/ikar-admin.service /etc/systemd/system/

# Przeładuj daemony
sudo systemctl daemon-reload

# Uruchom usługę
sudo systemctl start ikar-admin.service

echo "Usługa ikar-admin została przeładowana z symlinkiem."