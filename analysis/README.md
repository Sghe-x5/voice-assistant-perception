# Дополнительные анализы

| Раздел | Что проверяет | Команда из корня |
|---|---|---|
| [validation](validation/README.md) | Независимая арифметика и порядковая структура | `.venv/bin/python analysis/validation/check_arithmetic.py` |
| [validation](validation/README.md) | Полихорические корреляции и ULS-диагностика | `.venv/bin/python analysis/validation/ordinal_structure.py` |
| [lexical](lexical/SUMMARY.md) | Добавочную информацию из текстов AI-идей | `.venv/bin/python analysis/lexical/analyze_lexical.py` |

Сначала нужен основной расчёт: `scripts/run_all.py --download`. Лексическая
проверка уже входит в него; повторять её отдельно без изменений не требуется.
Остальные проверки независимы от основного анализа. Это не новые участники
и не доказательство валидности общего фактора интеллекта.
## Additional public-release audit

[Generalization data](generalization/README.md): pinned Vafa et al. CSV audit,
question-overlap checks and two independently reproduced non-text baselines.
This endpoint is belief change, not perceived intelligence; it stays separate
from the three primary datasets and their reproduction runner.
