#!/bin/zsh
# Раз в час (launchd ru.deford.balance-stati, минута 45): открыть на Тильде статьи Баланса, чей час настал
# (tilda/raspisanie.tsv). Сбой – сразу авария Еве и Артёму (правило 15.11.2026), а не тишина, как с 11 по 15.11.
cd "$(dirname "$0")"
echo "== $(date '+%Y-%m-%d %H:%M')"
if ! /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 publish_due.py; then
  ~/.claude/shablony/avariya.sh "Balance (balance-fit.ru)" "публикация статей по расписанию упала (publish_due.py), см. tilda/launchd.log" "чат статей Баланса"
  exit 1
fi
