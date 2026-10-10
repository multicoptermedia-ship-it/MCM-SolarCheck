# Online-Projektzugriff: Sicherheitsgrenze

Die gemeinsame Oberfläche darf Online-Projekte ausschließlich über eine serverseitig authentifizierte Benutzeridentität abrufen. Der neue Adapter `authorized_online_projects` verlangt eine bereits geprüfte Kunden-ID, ruft die vorhandene `customer_entry`-Berechtigungsprüfung auf und nutzt danach ausschließlich `projects_for_customer(customer_id)`. Er akzeptiert keine Benutzer-ID aus einer Browser-Abfrage als vertrauenswürdig.

Der bestehende Online-HTTP-Server verwaltet Anmeldung und Session-Cookies. Die neue Projektion ist noch **nicht** als HTTP-Route dort angeschlossen; eine Route muss zuerst `_require_customer_user()` oder eine gleichwertige Sessionprüfung ausführen. Der Offline-Vorschauserver darf keine Online-Identität simulieren. Demo-, Zahlungs- und Exportregeln bleiben unverändert.
