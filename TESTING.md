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

Zakres testów:
- `tests/test_app.py`:
  - Render HTML dla `/ikaros`, `/ikaros/terminal`, `/ikaros/logs`.
  - Sprawdza poprawność statusów i linków na stronie Connect.
  - Weryfikuje, że w UI nie ma już przycisków start/stop.
  - Testy API dla `/ikaros/status`, `/ikaros/start`, `/ikaros/stop` pozostają bez zmian.
- `tests/test_evaluator.py`:
  - Testy jednostkowe dla bezpiecznego ewaluatora warunku `available`.
- `tests/test_service_logic.py`:
  - Testy jednostkowe dla logiki startu i stopu usług, w tym `pid_file`, `workdir`, `env` i health-checków.

## Testy ręczne (w przeglądarce i CLI)
1. **Nawigacja i wygląd**
   - Otwórz http://localhost/ikaros (lub port 8602).
   - Sprawdź, czy widać ciemny motyw i nawigację "Connect | Terminal | Logs".
   - Przełączaj się między zakładkami, sprawdzając, czy podświetlenie aktywnej zakładki działa.
2. **Strona Connect**
   - Zweryfikuj, czy lista usług i ich statusy (UP/DOWN/MISSING) są poprawne.
   - Sprawdź, czy linki "Open" działają dla aktywnych usług z portem.
3. **Web Terminal**
   - Otwórz zakładkę "Terminal".
   - Sprawdź, czy terminal się pojawia i można w nim pisać komendy (np. `ls -la`, `echo 'hello'`).
   - Przetestuj zmianę rozmiaru okna przeglądarki – terminal powinien się dopasować.
4. **Strona Logs**
   - Otwórz zakładkę "Logs".
   - Domyślnie powinny być widoczne logi "Events".
   - Wybierz inną usługę z listy i sprawdź, czy jej logi się ładują.
   - Przetestuj filtrowanie, wpisując frazę w pole filtra.
   - Sprawdź przycisk "Pause/Resume".
5. **API (bez zmian)**
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
