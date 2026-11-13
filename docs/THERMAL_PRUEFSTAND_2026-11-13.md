# Thermal-Bestand und mittiger Temperaturmesspunkt – 13.11.2026

Der Nutzer erinnert an bereits untersuchte radiometrische M3T-Dateien und den mittigen Temperaturmesspunkt. Diese Bestandsprüfung liest ausschließlich vorhandene Dokumentation, Quellcode, Tests, Git-Historie und CI. Keine Originalbilder, Archive oder Kundendaten wurden erneut untersucht.

## Bereits vorhanden – weiterverwenden

| Teil | Gefundener Nachweis | Reichweite |
| --- | --- | --- |
| Radiometrischer Rohdatenbestand | [Originaldatenbericht](research/M3T_DATASET_VALIDATION_2025-08-25.md): 242/242 Dateien mit 655.360 APP3-Bytes, 640×512×16 Bit, little-endian | Historisch dokumentierte strukturelle Untersuchung dieses Bestands; keine erneute Originalprüfung und keine pauschale Aussage über andere Dateivarianten |
| Decoder und Hilfsblöcke | [M3TRadiometricParser](../src/mcm_solarcheck/thermal/m3t_radiometric.py), [vier Parsertests](../tests/test_m3t_radiometric.py) | Vollständige 327.680 Rohwerte, APP4/APP5-Struktur, Ende der APP-Kette und Ablehnung unvollständiger Daten |
| Rasterausrichtung | [Vorhandener Referenzplan](research/M3T_RADIOMETRIC_REFERENCE_PLAN.md): dokumentierter Vergleich mit gerendertem Bild | Native Orientierung wird unterstützt; keine Temperaturkalibrierung daraus ableiten |
| Rohwertstatistik/Anomalievorschläge | [Analyse/Qualitätstests](../tests/test_thermal_analysis_quality.py), vorhandene Thermal-Import-/Projektbausteine | Statistiken, Rohwertabweichungen, Kandidatenkoordinaten und Qualitätsgrenzen sind implementiert; keine bestätigten Defekte oder Celsiuswerte |
| Mittiger Temperaturpunkt | Nutzerhinweis und [bestehende Ablaufdokumentation](EXTERNES_RGB_ORTHOFOTO_GEOTIFF.md#thermal-darstellung-und-temperaturwerte-unterscheiden) | Bereits untersuchte Kontrollreferenz laut Nutzer; nicht erneut als unbekannte Dateieigenschaft behandeln |

Die vier Parsertests und fünf Analyse-/Qualitätstests arbeiten synthetisch. Der Originaldatenbericht dokumentiert einen früheren privaten Lauf. Diese Nachweisarten bleiben getrennt. Der aktuelle Branch `bf9392cf` hatte alle drei CI-Workflows erfolgreich, darunter die vollständige Python-Testsuite; keine neue Originalinventur ist nötig.

## Was im aktuellen Code noch fehlt

[DJIReferenceTemperatureProvider](../src/mcm_solarcheck/thermal/temperature_provider.py) ist weiterhin ein Platzhalter: `convert_file()` löst ausdrücklich `TemperatureConversionUnavailable` aus. Die Git-Historie dieses Providers enthält dessen Anlage, keine nachfolgende implementierte Konvertierung. Der bestehende [M3TImporter](../src/mcm_solarcheck/importers/m3t.py) setzt `temperature_matrix=None`; Anomalievorschläge tragen unkalibrierte Rohwerte.

Ein abgeschlossener Test, der den mittigen Messwert ausliest, einer verifizierten Rohpixelposition zuordnet und damit eine vollständige Celsiusmatrix gegen unabhängige Referenzen bestätigt, wurde im aktuellen Branch und den untersuchten Quellen nicht gefunden. Das widerlegt keine weitergehende private Untersuchung in einem früheren Chat; deren reproduzierbarer Code-/Testnachweis liegt hier derzeit nicht vor. Den vorhandenen radiometrischen Decoder deshalb nicht erneut entwickeln.

Ein bekannter Temperaturwert in der Mitte ist ein sinnvoller Kontrollwert. Er bestimmt allein weder die gesamte Umrechnungskurve noch räumliche/Umgebungsparameter für alle Pixel. Die vorhandenen [APP4-/APP5-Befunde](research/M3T_APP4_APP5_ANALYSIS.md) enthalten noch ungeprüfte Parametersemantik. Keine Skala/Temperaturformel raten und den Mittelpunkt nicht ungeprüft als vollständige Kalibrierung ausweisen.

## Nächster vertikaler Schritt

1. Thermal-Orthofoto desselben bereits erfolgreichen RGB-Projekts mit etablierter freier Software vorbereiten; vorhandenen Import, Paarzuordnung und Rohdatenparser wiederverwenden. Keine neue ZIP-/EXIF-/Rohdaten-Grunduntersuchung.
2. Eigene Thermal-Sensorgeometrie und räumliche Deckung mit RGB prüfen; keine RGB-Intrinsics übernehmen. Originale und 16-Bit-Rohdaten bleiben lokal und unverändert. Ein farblich bearbeitetes Mosaik ist keine wertgetreue Temperaturmatrix.
3. Vorhandene Rohwert-/Anomalievorschläge und Modul-/Review-Kette verbinden. Visuelle beziehungsweise relative Vorschläge als ungeprüft kennzeichnen. °C-/ΔT-Befunde erst mit verifizierter Umrechnung und Werteerhalt im geometrischen Folgeprodukt ausweisen.

Dies ist keine neue Aufforderung zu Kalibrierdateien, SDK-Installation oder zum Start einer Untersuchungsserie. Keine proprietäre DJI-SDK-Integration ist dadurch freigegeben. Temperaturumrechnung und Orthofotogeometrie sind getrennte Aufgaben; vorhandene Nachweise erhalten und gezielt an der tatsächlichen Lücke fortsetzen. Die Anlagenart-/Dachqualifikation bleibt ein eigener späterer Block.
