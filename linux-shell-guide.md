# Przewodnik po podstawowych poleceniach Linux Shell

## Wstęp

Ten przewodnik zawiera najważniejsze polecenia powłoki Linux (bash), które każdy użytkownik powinien znać. Są one podstawą pracy z systemem Linux - od nawigacji po pliki, przez zarządzanie procesami, aż po diagnostykę systemu. Wszystkie przykłady zakładają pracę w terminalu z powłoką bash.

## Nawigacja po systemie plików

### pwd - print working directory (pokaż bieżący katalog)
```bash
pwd
```
Wyświetla pełną ścieżkę do aktualnego katalogu roboczego.

### ls - list (lista plików i katalogów)
```bash
ls                    # podstawowa lista
ls -l                 # long listing - szczegółowa lista z uprawnieniami
ls -a                 # all - pokaż ukryte pliki (zaczynające się od .)
ls -h                 # human readable - rozmiary w czytelnej formie
ls -la                # kombinacja powyższych
```

### cd - change directory (zmień katalog)
```bash
cd /home/user         # przejdź do konkretnego katalogu
cd ..                 # poziom wyżej
cd ~                  # do katalogu domowego (home)
cd -                  # do poprzedniego katalogu
```

### find - znajdź pliki
```bash
find . -name "*.txt"  # znajdź wszystkie pliki .txt w bieżącym katalogu
find /home -type f -name "config*"  # znajdź pliki zaczynające się od "config"
```

## Zarządzanie plikami i katalogami

### mkdir - make directory (utwórz katalog)
```bash
mkdir nowy_katalog
mkdir -p sciezka/do/nowego/katalogu  # parents - utwórz całą ścieżkę
```

### touch - utwórz pusty plik lub zaktualizuj datę
```bash
touch nowy_plik.txt
```

### cp - copy (kopiuj pliki/katalogi)
```bash
cp plik1.txt plik2.txt              # kopiuj plik
cp -r katalog1 katalog2             # recursive - kopiuj katalog rekursywnie
cp *.txt /backup/                   # kopiuj wszystkie .txt do katalogu
```

### mv - move (przenieś/zmień nazwę)
```bash
mv stary.txt nowy.txt               # zmień nazwę
mv plik.txt /nowa/sciezka/          # przenieś plik
mv katalog /nowa/lokalizacja/       # przenieś katalog
```

### rm - remove (usuń pliki/katalogi)
```bash
rm plik.txt                         # usuń plik
rm -r katalog                       # recursive - usuń katalog rekursywnie
rm -rf katalog                      # force - wymuś usunięcie (nie pytaj o potwierdzenie)
```

### cat - concatenate (wyświetl zawartość pliku)
```bash
cat plik.txt                        # wyświetl cały plik
cat plik1.txt plik2.txt             # połącz i wyświetl
```

### less/more - przeglądaj pliki
```bash
less plik.txt                       # przeglądaj plik (q - wyjście)
more plik.txt                       # podobny, ale mniej funkcji
```

### head/tail - początek/koniec pliku
```bash
head plik.txt                       # pierwsze 10 linii
head -20 plik.txt                   # pierwsze 20 linii
tail plik.txt                       # ostatnie 10 linii
tail -f plik.txt                    # follow - obserwuj zmiany na końcu (logi)
```

### grep - global regular expression print (szukaj tekstu w plikach)
```bash
grep "szukany_tekst" plik.txt       # znajdź linię z tekstem
grep -r "tekst" /katalog/           # recursive - szukaj rekursywnie
grep -i "tekst" plik.txt            # ignore case - ignoruj wielkość liter
```

## Zarządzanie procesami

### ps - process status (pokaż procesy)
```bash
ps                    # procesy w bieżącym terminalu
ps aux                # all users extra - wszystkie procesy szczegółowo
ps -ef                # extended full - wszystkie procesy w formacie pełnym
```

### top/htop - monitor procesów
```bash
top                   # table of processes - interaktywny monitor (q - wyjście)
htop                  # lepsza wersja top (jeśli zainstalowana)
```

### kill - zabij proces
```bash
kill 1234             # zabij proces o PID 1234
kill -9 1234          # wymuś zabicie (SIGKILL)
killall firefox       # zabij wszystkie procesy o nazwie firefox
```

### jobs - pokaż zadania w tle
```bash
jobs                  # lista zadań w tle
fg %1                 # foreground - przywróć zadanie nr 1 do pierwszego planu
bg %1                 # background - uruchom zadanie nr 1 w tle
```

## Zarządzanie użytkownikami i uprawnieniami

### whoami - kto jestem
```bash
whoami
```

### id - informacje o użytkowniku
```bash
id                    # UID, GID i grupy
```

### chmod - change mode (zmień uprawnienia)
```bash
chmod 755 plik.txt    # rwxr-xr-x
chmod +x skrypt.sh    # dodaj prawo wykonania
chmod -R 755 katalog/ # recursive - rekursywnie dla katalogu
```

### chown - change owner (zmień właściciela)
```bash
chown user:group plik.txt
chown -R user:group katalog/  # recursive - rekursywnie
```

### sudo - superuser do (wykonaj jako root)
```bash
sudo komenda          # wykonaj komendę jako administrator
sudo -i               # interactive - przejdź do powłoki root
```

## Sieć i połączenia

### ping - sprawdź połączenie
```bash
ping google.com       # pinguj do czasu przerwania (Ctrl+C)
ping -c 4 google.com  # tylko 4 pakiety
```

### curl - pobierz dane z URL
```bash
curl http://example.com               # pobierz stronę
curl -I http://example.com            # tylko nagłówki
curl -O http://example.com/plik.zip   # pobierz plik
```

### wget - pobierz pliki
```bash
wget http://example.com/plik.zip
wget -c http://example.com/duzy.zip    # kontynuuj pobieranie
```

### ss/netstat - sprawdź połączenia
```bash
ss -tlnp              # TCP nasłuchujące porty
ss -tulnp             # wszystkie nasłuchujące porty
netstat -tlnp         # podobny efekt (starsze narzędzie)
```

### ifconfig/ip - konfiguracja sieci
```bash
ip addr show          # pokaż adresy IP
ip route show         # pokaż tablicę routingu
ifconfig              # starsze narzędzie do interfejsów
```

## System i diagnostyka

### df - disk free (miejsce na dysku)
```bash
df -h                 # human readable - miejsce w czytelnej formie
df -i                 # inodes - inody zamiast bloków
```

### du - disk usage (rozmiar plików/katalogów)
```bash
du -h katalog/        # rozmiar katalogu
du -sh *              # summarize human - rozmiary wszystkich plików w katalogu
```

### free - pamięć RAM
```bash
free -h               # human readable - pamięć w czytelnej formie
```

### uname - unix name (informacje o systemie)
```bash
uname -a              # all - wszystkie informacje
uname -r              # release - wersja kernela
```

### uptime - czas pracy systemu
```bash
uptime
```

### dmesg - display message (logi kernela)
```bash
dmesg | tail          # ostatnie logi
dmesg | grep error    # błędy w logach
```

## Przydatne narzędzia i triki

### history - historia komend
```bash
history               # pokaż historię
!123                  # wykonaj komendę nr 123 z historii
!!                    # wykonaj ostatnią komendę
```

### alias - skróty komend
```bash
alias ll='ls -la'     # utwórz alias
alias                  # pokaż wszystkie aliasy
```

### which - znajdź lokalizację programu
```bash
which python          # gdzie jest python
```

### man - podręcznik
```bash
man ls                # dokumentacja dla ls
man -k keyword        # szukaj w dokumentacji
```

### echo - wyświetl tekst
```bash
echo "Hello World"
echo $PATH            # wyświetl zmienną środowiskową
```

### date - data i czas
```bash
date                  # aktualna data/czas
date +"%Y-%m-%d"      # formatowana data
```

### wc - word count (zlicz linie/słowa/znaki)
```bash
wc plik.txt           # linie, słowa, znaki
wc -l plik.txt        # lines - tylko linie
```

### sort - sortuj
```bash
sort plik.txt         # sortuj alfabetycznie
sort -n liczby.txt    # numeric - sortuj numerycznie
sort -r plik.txt      # reverse - odwrotnie
```

### uniq - unique (usuń duplikaty)
```bash
uniq plik.txt         # usuń kolejne duplikaty linii
uniq -c plik.txt      # count - policz wystąpienia
```

### tar - tape archive (archiwizacja)
```bash
tar -cvf archiwum.tar katalog/     # create verbose file - utwórz archiwum
tar -xvf archiwum.tar              # extract verbose file - rozpakuj
tar -czvf archiwum.tar.gz katalog/ # create gzip - skompresuj gzip
tar -xzvf archiwum.tar.gz          # extract gzip - rozpakuj gzip
```

### gzip/bzip2 - kompresja
```bash
gzip plik.txt        # skompresuj (stworzy plik.txt.gz)
gunzip plik.txt.gz   # rozpakuj
bzip2 plik.txt       # lepsza kompresja
bunzip2 plik.txt.bz2
```

## Potoki i przekierowania

### | - potok (pipe)
```bash
ps aux | grep python  # znajdź procesy python
ls -la | less         # przeglądaj długą listę
```

### > - przekieruj wyjście
```bash
echo "tekst" > plik.txt    # zapisz do pliku (nadpisz)
komenda > plik.log 2>&1    # wyjście i błędy do pliku
```

### >> - dopisz do pliku
```bash
echo "tekst" >> plik.txt   # dopisz do pliku
```

### < - wejście z pliku
```bash
komenda < plik.txt
```

### && i || - operatory logiczne
```bash
komenda1 && komenda2  # wykonaj komenda2 jeśli komenda1 się udała
komenda1 || komenda2  # wykonaj komenda2 jeśli komenda1 się nie udała
```

## Zmienne środowiskowe

### env - pokaż zmienne
```bash
env                   # wszystkie zmienne środowiskowe
echo $HOME            # wartość zmiennej
```

### export - ustaw zmienną
```bash
export MOJA_ZMIENNA="wartość"
echo $MOJA_ZMIENNA
```

## Wyszukiwanie i znajdowanie

### locate - szybkie znajdowanie plików
```bash
locate plik.txt       # znajdź plik (wymaga updatedb)
```

### updatedb - zaktualizuj bazę locate
```bash
sudo updatedb         # zaktualizuj bazę plików
```

## Zarządzanie pakietami (Ubuntu/Debian)

### apt - zarządzanie pakietami
```bash
sudo apt update       # zaktualizuj listę pakietów
sudo apt upgrade      # zaktualizuj pakiety
sudo apt install pakiet
sudo apt remove pakiet
sudo apt search pakiet # szukaj pakietów
```

## Zarządzanie usługami systemd

### systemctl - kontroluj systemd
```bash
sudo systemctl start nazwa_uslugi     # uruchom usługę
sudo systemctl stop nazwa_uslugi      # zatrzymaj usługę
sudo systemctl restart nazwa_uslugi   # zrestartuj usługę
sudo systemctl status nazwa_uslugi    # sprawdź status
sudo systemctl enable nazwa_uslugi    # włącz autostart
sudo systemctl disable nazwa_uslugi   # wyłącz autostart
sudo systemctl daemon-reload          # przeładuj konfigurację
```

### Kopiowanie plików konfiguracyjnych usług
```bash
# Kopiowanie pliku usługi do systemd
sudo cp /workspace/ikar_apps/ikar-admin/systemd/ikar-admin.service /etc/systemd/system/

# Lub utworzenie symlinka (lepsze rozwiązanie - aktualizacje automatycznie)
sudo ln -sf /workspace/ikar_apps/ikar-admin/systemd/ikar-admin.service /etc/systemd/system/

# Przeładowanie systemd i uruchomienie
sudo systemctl daemon-reload
sudo systemctl enable ikar-admin.service
sudo systemctl start ikar-admin.service
```

### Sprawdzanie logów usług
```bash
# Logi konkretnej usługi
journalctl -u ikar-admin.service

# Logi z ostatniej godziny
journalctl -u ikar-admin.service --since "1 hour ago"

# Śledzenie logów w czasie rzeczywistym
journalctl -u ikar-admin.service -f
```

## Podsumowanie

To podstawowe polecenia, które pozwolą Ci efektywnie pracować z systemem Linux. Pamiętaj:

- Używaj `man komenda` lub `komenda --help` aby poznać szczegóły
- Kombinuj polecenia z potokami (`|`) dla potężnych operacji
- Zawsze sprawdzaj co robisz, szczególnie z `rm -rf` i `sudo`
- Ćwicz w bezpiecznym środowisku (maszyna wirtualna)

Powodzenia w eksploracji Linuxa! 🐧