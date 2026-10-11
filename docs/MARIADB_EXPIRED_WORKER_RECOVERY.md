# MariaDB: Vorbereitung der Worker-Ausfall-Recovery

Die neuen Komponenten klassifizieren Slot-/Job-Paare ausschließlich lesend: `empty`, `active`, `expired_requires_quiescence` und `manual_review`. Ein abgelaufenes Lease allein beweist nicht, dass ein externer CPU-/GPU-Worker beendet wurde. `MariaDBRecoveryAdvice.may_reassign` bleibt daher in allen Fällen `False`.

Vor einer späteren automatischen Wiedervergabe sind mindestens erforderlich: überprüfbare Stilllegung oder echtes externes Fencing des alten Workers; ein transaktionaler, token- und generationsgebundener Recovery-Übergang für Job und Slot; sichere Behandlung bereits veröffentlichter Ergebnisse; Auditierung; Wiederanlauf-/Crash-Tests. Eine Freigabe allein anhand eines Zeitstempels wäre unsicher.

Die Inspektion verwendet derzeit die injizierte Anwendungszeit und erwartet naive UTC-Datetime-Werte aus dem DB-Treiber; vor produktiver Nutzung sind Serverzeit-/Zeitzonen-Semantik und Isolation ausdrücklich zu verifizieren. Es gibt keinen automatischen Reset, keine Verbindung zur Live-Queue, keine IONOS-Migration, keine Secrets und keinen Merge nach `main`.
