#!/bin/bash

PORT=8621
PID=$(lsof -ti:$PORT || echo "")

if [ ! -z "$PID" ]; then
  echo "⏹️  Zatrzymuję proces $PID na porcie $PORT..."
  kill $PID

  # Czekaj aż proces się zakończy
  while kill -0 $PID 2>/dev/null; do
    sleep 0.5
  done

  echo "✅ Proces zatrzymany"
else
  echo "ℹ️  Brak procesu na porcie $PORT"
fi

echo "🔌 Port $PORT jest wolny"