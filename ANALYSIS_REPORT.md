# Raport z Analizy Aplikacji: ikar-admin

Data: 2025-10-12
Autor Analizy: Gemini

## 1. Podsumowanie (High-Level Summary)

**Cel aplikacji:** `ikar-admin` to minimalistyczny panel administracyjny stworzony jako usługa FastAPI. Jego głównym celem jest dostarczenie prostego interfejsu (zarówno webowego, jak i API) do monitorowania i zarządzania cyklem życia lokalnych usług, takich jak ComfyUI, code-server, Filebrowser i Tailscale.

**Rozwiązywany problem:** Aplikacja centralizuje kontrolę nad wieloma niezależnymi usługami, które mogą działać w tym samym środowisku. Upraszcza proces ich uruchamiania, zatrzymywania oraz sprawdzania statusu i logów, eliminując potrzebę ręcznego wykonywania komend w terminalu dla każdej z nich.

## 2. Architektura (Architecture Overview)

Aplikacja jest zbudowana w oparciu o framework **FastAPI**, co zapewnia wysoką wydajność i automatyczną dokumentację (choć w tym przypadku jest ona wyłączona).

-   **Punkt wejściowy (`main.py`):** Główny plik aplikacji, który tworzy instancję FastAPI. Definiuje wszystkie endpointy API w ramach `APIRouter` z prefiksem `/ikaros`. Odpowiada również za renderowanie interfejsu użytkownika w formacie HTML.
-   **Logika Biznesowa (`service_manager.py`):** Ten moduł stanowi serce aplikacji. Odpowiada za definicję, wykrywanie i zarządzanie usługami.
    -   **Klasa `Service`:** Struktura danych (`@dataclass`) przechowująca wszystkie informacje o danej usłudze (nazwa, komendy start/stop, ścieżka logu, port, dostępność).
    -   **`build_services()`:** Funkcja-fabryka, która tworzy i zwraca słownik skonfigurowanych obiektów `Service`. Konfiguracja jest w dużej mierze zakodowana na stałe (hardcoded).
    -   **Wykrywanie procesów:** Logika opiera się na przeszukiwaniu `cmdline` w systemie plików `/proc` oraz sprawdzaniu, czy porty są otwarte. W przypadku dostępności `systemd`, preferowane jest użycie `systemctl`.
-   **Interfejs Użytkownika (UI):** Aplikacja serwuje pojedynczą stronę HTML (`index()` w `main.py`), która jest dynamicznie generowana po stronie serwera. Strona zawiera tabelę z listą usług i ich statusem. Interakcje (start/stop, odświeżanie statusu, podgląd logów) są realizowane za pomocą **czystego JavaScriptu (Vanilla JS)**, który komunikuje się z endpointami API aplikacji.
-   **Routing:** Wszystkie ścieżki są zgrupowane pod prefiksem `/ikaros`, co ułatwia integrację z reverse proxy (np. Nginx).

Struktura jest prosta i czytelna, z wyraźnym podziałem odpowiedzialności między warstwą prezentacji/API (`main.py`) a logiką zarządzania usługami (`service_manager.py`).

## 3. Kluczowe Funkcjonalności (Key Features)

### Interfejs Użytkownika (UI)
-   **Dashboard:** Główny widok prezentujący listę monitorowanych usług.
-   **Status Usługi:** Każda usługa ma czytelny status: `UP` (działa), `DOWN` (zatrzymana) lub `MISSING` (niedostępna/niezainstalowana).
-   **Kontrola Usług:** Przyciski "Start" i "Stop" do zarządzania każdą z usług. Przyciski są nieaktywne dla usług oznaczonych jako `MISSING`.
-   **Podgląd Logów:** Zintegrowany widok do przeglądania ostatnich wpisów z centralnego logu zdarzeń (`ikar-admin-events.log`).
-   **Szybki Dostęp:** Bezpośrednie linki do interfejsów webowych zarządzanych usług (np. ComfyUI, code-server).

### API
-   `GET /ikaros`: Zwraca główny panel w formacie HTML.
-   `GET /ikaros/health`: Zwraca szczegółowy raport o stanie systemu w formacie JSON (wykorzystanie dysku, status portów, status usług).
-   `GET /ikaros/status`: Zwraca uproszczony status (true/false) dla każdej usługi.
-   `GET /ikaros/events`: Zwraca `N` ostatnich linii z centralnego pliku logów zdarzeń.
-   `GET /ikaros/logs/{svc}`: Zwraca `N` ostatnich linii z pliku logu dla konkretnej usługi.
-   `POST /ikaros/start/{svc}`: Uruchamia wskazaną usługę.
-   `POST /ikaros/stop/{svc}`: Zatrzymuje wskazaną usługę.

## 4. Zależności (Dependencies)

Zgodnie z plikiem `requirements.txt`, główne zależności Pythonowe to:
-   `fastapi`: Nowoczesny framework webowy.
-   `uvicorn`: Serwer aplikacyjny ASGI.
-   `httpx`: Klient HTTP używany przez `TestClient` w testach.

Aplikacja ma również **niejawne zależności** od narzędzi i struktury systemu operacyjnego Linux:
-   Dostęp do systemu plików `/proc` do wyszukiwania procesów.
-   Standardowe polecenia powłoki: `pkill`, `tail`, `shutil.which`.
-   Opcjonalnie: `sudo` (dla `systemctl` i `tailscaled`) skonfigurowane do działania bez hasła (`NOPASSWD`).

## 5. Strategia Testowania (Testing Strategy)

Projekt posiada solidny zestaw zautomatyzowanych testów, znajdujący się w `tests/test_app.py`. Testy wykorzystują `TestClient` z FastAPI do symulowania zapytań HTTP do aplikacji bez uruchamiania serwera sieciowego.

**Zakres testów:**
-   **Renderowanie UI:** Sprawdzenie, czy główny panel HTML jest poprawnie generowany i zawiera oczekiwane elementy.
-   **Endpointy JSON:** Weryfikacja poprawności struktury i typów danych zwracanych przez `/status` i `/health`.
-   **Akcje Start/Stop:** Testowanie, czy endpointy `POST` działają poprawnie, zarówno przy odpowiedzi JSON, jak i przy przekierowaniu 303 (dla formularzy HTML).
-   **Obsługa Błędów:** Sprawdzenie, czy zapytania dotyczące nieznanych usług zwracają błąd 404.
-   **Logika Usług `MISSING`:** Testowanie (z użyciem `monkeypatch`), czy niedostępna usługa jest poprawnie oznaczana w UI (przycisk `disabled`) i czy API zwraca odpowiedni komunikat błędu.
-   **Endpointy logów:** Weryfikacja, czy endpointy `/logs/...` i `/events` zwracają dane w formacie `text/plain`.

Strategia testowania jest kompleksowa jak na rozmiar aplikacji i pokrywa kluczowe ścieżki działania, co znacząco podnosi jej niezawodność.

## 6. Wnioski i Spostrzeżenia (Conclusions & Insights)

### Mocne Strony
-   **Prostota i Skupienie:** Aplikacja robi jedną rzecz i robi ją dobrze. Jest lekka i ma jasno zdefiniowany cel.
-   **Czysta Architektura:** Wyraźny podział na warstwę API i logikę serwisową ułatwia zrozumienie i ewentualną rozbudowę kodu.
-   **Brak Zależności Frontendowych:** Użycie czystego JavaScriptu sprawia, że interfejs jest bardzo lekki i nie wymaga skomplikowanego procesu budowania.
-   **Dobra Jakość Kodu:** Kod jest czytelny, a użycie `@dataclass` i nowoczesnych funkcji Pythona świadczy o dobrych praktykach.
-   **Solidne Testy:** Wysokie pokrycie kodu testami automatycznymi jest dużym atutem, zapewniającym stabilność.
-   **Elastyczność w Wykrywaniu Usług:** Aplikacja potrafi korzystać z `systemd`, ale posiada też mechanizmy rezerwowe (sprawdzanie procesów/portów), co czyni ją bardziej uniwersalną.

### Potencjalne Obszary do Poprawy i Ryzyka
-   **Bezpieczeństwo (Krytyczne Ryzyko):** Największą słabością aplikacji jest **całkowity brak mechanizmów uwierzytelniania i autoryzacji**. Każdy, kto ma dostęp do portu aplikacji, może dowolnie zarządzać usługami. Wymaganie `sudo NOPASSWD` dla niektórych operacji stanowi dodatkowe, poważne ryzyko bezpieczeństwa.
-   **Konfiguracja "Hardcoded":** Definicje usług są zaszyte bezpośrednio w kodzie (`service_manager.py`). Przeniesienie ich do zewnętrznego pliku konfiguracyjnego (np. `config.yaml`) znacznie zwiększyłoby elastyczność i ułatwiło dodawanie nowych usług bez modyfikacji kodu.
-   **Kruchość Zarządzania Procesami:** Poleganie na `pkill -f` z dopasowaniem do wzorca bywa zawodne. Bardziej jednoznaczny wzorzec lub zarządzanie numerami PID (zapisywanymi przy starcie usługi) byłoby solidniejszym rozwiązaniem.
-   **Przenośność:** Silne uzależnienie od specyfiki systemu Linux (np. `/proc`, `pkill`) ogranicza możliwość uruchomienia aplikacji na innych systemach operacyjnych (np. macOS, Windows).
