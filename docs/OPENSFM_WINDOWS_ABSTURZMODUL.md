# Vorhandenen Windows-Absturzbericht auf das Fehlermodul begrenzen

**OPEN-SFM-GPU-02: Nutzer meldet0xC0000005 nach worker_complete und gültigem JSON.** Damit ist der Worker bis hinter seine Berichtsausgabe gelangt, nicht jedoch sauber beendet. Der Inhalt seines Teilberichts ist in der alten Elternausgabe nicht enthalten: erfolgreiche Geräteabfrage oder Fehlerbericht bleiben zu unterscheiden. Keine bestätigte GPU-Erkennung/Matching-/Dense-Freigabe. Quellbau/Installation bleiben abgeschlossen. [Checkpoint](AKTUELLER_ENTWICKLUNGSSTAND.md).


**Abgeschlossen:** Nutzer hat zwei gleiche Treffer geliefert: ntdll.dll10.0.19041.6456,0xC0000005,Offset0000000000024785. Das lokalisiert die Erkennungsstelle, nicht die ursprüngliche Ursache. Keine Windows-DLL-Reparatur/Neuinstallation daraus ableiten. Die Abfrage unten ist Historie und wird nicht wiederholt. Als nächster begrenzter Schritt [regulären OpenSfM-Importeinstieg vergleichen](OPENSFM_STANDARDSTART_WINDOWS10.md); keine Variantenserie.

Der abgeschlossene Schritt las vorhandene lokale Windows-Application-Error-Ereignisse der letzten zwei Stunden und gibt nur Einträge für `E:\SolarCheck-OpenSfM\env\python.exe` aus. Nur DLL-/Modulbasename, numerische Version, Exceptioncode und Moduloffset, höchstens drei Treffer. Keine Rohmeldung, Pfade, Computer-/Benutzernamen, Report-IDs, Dumps, Fotos oder Projektdateien übertragen. Kein neuer GPU-Lauf/Download, kein Installer/Neustart oder Registryzugriff durch diesen Block. Normale Windows-PowerShell verwenden.

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $ausgabe = @{ check='solarcheck-opensfm-crash-module-1'; status='not_found'; faults=@() }
    try {
        $ereignisse = @(Get-WinEvent -FilterHashtable @{
            LogName='Application'
            ProviderName='Application Error'
            Id=1000
            StartTime=(Get-Date).AddHours(-2)
        } -MaxEvents 50)
    } catch {
        if ($_.FullyQualifiedErrorId -notlike 'NoMatchingEventsFound*') { $ausgabe.status='unavailable' }
        $ausgabe | ConvertTo-Json -Depth 4
        return
    }
    foreach ($ereignis in $ereignisse) {
        [xml]$xml = $ereignis.ToXml()
        $knoten = @($xml.SelectNodes("//*[local-name()='EventData']/*[local-name()='Data']"))
        $daten = @{}
        foreach ($k in $knoten) {
            if ($k.GetAttribute('Name')) { $daten[$k.GetAttribute('Name')] = $k.InnerText }
        }
        if (-not $daten.ContainsKey('AppPath') -and $knoten.Count -ge 12) {
            $daten['AppPath']=$knoten[10].InnerText
            $daten['ModuleName']=$knoten[3].InnerText
            $daten['ModuleVersion']=$knoten[4].InnerText
            $daten['ExceptionCode']=$knoten[6].InnerText
            $daten['FaultingOffset']=$knoten[7].InnerText
        }
        if ($daten['AppPath'] -ine 'E:\SolarCheck-OpenSfM\env\python.exe') { continue }
        $modul = [IO.Path]::GetFileName([string]$daten['ModuleName'])
        if ($modul -notmatch '^[A-Za-z0-9_.+-]{1,128}$') { $modul='unknown' }
        $version = [string]$daten['ModuleVersion']
        if ($version -notmatch '^[0-9.]{1,48}$') { $version='unknown' }
        $code = [string]$daten['ExceptionCode']
        if ($code -match '^(?:0x)?([0-9a-fA-F]{8})$') { $code='0x'+$Matches[1].ToUpper() } else { $code='unknown' }
        $offset = [string]$daten['FaultingOffset']
        if ($offset -notmatch '^[0-9a-fA-F]{1,16}$') { $offset='unknown' }
        $ausgabe.faults += @{ module=$modul; version=$version; exception_code=$code; offset=$offset }
        if ($ausgabe.faults.Count -ge 3) { break }
    }
    if ($ausgabe.faults.Count) { $ausgabe.status='found' }
    $ausgabe | ConvertTo-Json -Depth 4
}
```

Nur diesen kleinen JSON-Block zurückmelden, auch bei `not_found`/`unavailable`. Ein Modulname grenzt die Untersuchung ein, beweist allein aber noch nicht die konkrete Ursache. Den bisherigen GPU-Test vorerst nicht erneut starten; keine frühen Exit-Tricks (`os._exit`) oder Abschaltung der Exitcodeprüfung zur Umdeutung eines Absturzes in PASS. Die bestehende Probe wurde zusätzlich so ergänzt, dass ein künftiger Crash einen begrenzten Teilberichtsstatus/Geräteanzahlen vor dem Beenden bewahrt; diese Informationen bleiben ausdrücklich ungeprüft und lösen kein Matching aus.
