# ikar-admin Testing Strategy

## Goals
- Upewnić się, że panel admina na 127.0.0.1:8602/ikaros działa lokalnie w dystrybucji ikaros.
- Zweryfikować, że reverse proxy Nginx pod http://127.0.0.1/ikaros (== http://localhost/ikaros z Windows) zwraca panel, a nie 502.
- Pokryć kluczowe scenariusze API: status usług, start/stop, logi, health, obsługa błędów.
- Zapewnić ręczne kroki kontrolne przy użyciu narzędzi dostępnych w WSL2 (curl/lynx), bez polegania na przeglądarce Windows.

## Środowisko
- Dystrybucja WSL `ikaros`.
- Użytkownik `dev`.
- Panel uruchamiany jako usługa systemd `ikar-admin.service` oraz serwowany przez Nginx.

## Automatyczne testy (pytest)
Polecenie uruchomienia (tworzy osobny venv):

```bash
bash /workspace/ikar_apps/ikar-admin/run_tests.sh
```

Zakres testów (`tests/test_app.py`):
- Render HTML dla `/ikaros` (sprawdza listę usług, przyciski, linki „Open”).
- `/ikaros/status` – poprawna struktura JSON.
- `/ikaros/start/{svc}` – zwraca JSON i ustawia `running=True`.
- `/ikaros/stop/{svc}` z nagłówkiem HTML – odpowiedź 303 i redirect z powrotem do `/ikaros`.
- `/ikaros/logs/{svc}` – tekstowy tail logów.
- `/ikaros/health` – zawiera pola `disk`, `ports`, `services`.
- Scenariusze błędne (w dodatkowych testach) – nieznana usługa zwraca 404.

## Testy ręczne (CLI w ikaros)
1. **Usługa działa**
   ```bash
   systemctl status ikar-admin --no-pager
   systemctl status nginx --no-pager
   ```
2. **Zdrowie backendu**
   ```bash
   curl -fsS http://127.0.0.1:8602/ikaros/health | jq
   ```
3. **Reverse proxy**
   ```bash
   curl -fsS http://127.0.0.1/ikaros/health | jq
   ```
4. **Widok HTML (tekstowo)** – wymaga pakietu `lynx` (instalacja `sudo apt-get install -y lynx`).
   ```bash
   lynx -dump http://127.0.0.1/ikaros/
   ```
   Oczekiwane: tabela z usługami (comfyui, code, filebrowser, tailscale) i linki `Logs`/`Open`.
5. **Akcje start/stop API**
   ```bash
   curl -fsS -X POST http://127.0.0.1:8602/ikaros/start/comfyui | jq
   curl -fsS -X POST http://127.0.0.1:8602/ikaros/stop/comfyui  | jq
   ```
   Przy braku instalacji (`MISSING`) odpowiedź zawiera `ok: false` i komunikat `Service not installed`.
   Przy działającym panelu z formularza HTML akcje przekierowują na `/ikaros` (303).

## Kiedy wykonać pełen zestaw
- Po zmianach w plikach `app/main.py`, `service_manager.py`, konfiguracji Nginx lub integracji systemd.
- Po aktualizacjach zależności (FastAPI, uvicorn itp.).
- Przed publikacją instrukcji dla RunPod/Windows.
