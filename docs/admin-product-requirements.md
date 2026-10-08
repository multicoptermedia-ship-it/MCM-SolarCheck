# SolarCheck Online – Admin- und Produktanforderungen

Dieses Dokument hält Anforderungen fest, die für die spätere produktive Adminoberfläche verbindlich berücksichtigt werden sollen.

## Pricing-Verwaltung

Die Adminoberfläche benötigt einen eigenen Bereich **Pricing**.

Administratoren müssen dort die SolarCheck-Leistungsstufen und deren Preise manuell pflegen können, damit das kommerzielle Angebot an aktuelle Marktgegebenheiten angepasst werden kann, ohne dafür Anwendungscode ändern oder neu ausrollen zu müssen.

### Anforderungen

- Leistungsstufen müssen administrierbar sein.
- Pro Leistungsstufe müssen mindestens Unter- und Obergrenze der Anlagenleistung (kWp) sowie der Preis gepflegt werden können.
- Preis und Währung müssen explizit gespeichert werden.
- Änderungen erzeugen eine **neue Tarifversion**; bereits verwendete Tarifversionen werden nicht überschrieben.
- Ein zukünftiger Tarif darf einen Zeitpunkt besitzen, ab dem er wirksam wird.
- Bestehende Payments behalten ihren bei Erstellung gespeicherten Tarif-Snapshot (tariff_version, plant_kwp, Betrag) und dürfen durch spätere Preisänderungen nicht rückwirkend verändert werden.
- Ungültige oder überlappende Leistungsstufen müssen serverseitig abgelehnt werden.
- Die Adminoberfläche darf nur die bestehende serverseitige Tarifdomäne administrieren; Preislogik darf nicht ausschließlich im GUI-Zustand liegen.
- Tarifänderungen sollen nachvollziehbar/auditierbar sein.

### Technische Grundlage

Die bestehende versionierte SolarCheck-Tarifdomäne und SQLiteSolarCheckTariffStore bleiben die maßgebliche Quelle. Die spätere Adminmaske soll darauf aufsetzen, statt eine separate Pricing-Datenhaltung einzuführen.

Diese Anforderung ist für den GUI/Admin-Block vorzumerken. Die laufende 10L-Integration wird dadurch nicht am aktuellen CI-Gate vorbeigeführt.
