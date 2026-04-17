# Betriebsvereinbarung zur Einführung und Nutzung der Ant Observation Agent Software

> **Template — mitbestimmungspflichtige Betriebsvereinbarung gem. BetrVG
> §87(1) Nr. 6** (Einführung und Anwendung von technischen Einrichtungen,
> die dazu bestimmt sind, das Verhalten oder die Leistung der
> Arbeitnehmer zu überwachen).
>
> Dieser Text ist ein Muster und MUSS vor Abschluss durch die
> Rechtsabteilung und den Betriebsrat des Kunden an das jeweilige
> Unternehmen angepasst werden. Ant Automations liefert als
> Auftragsverarbeiter den technischen Teil (§3, §5). Die
> betriebsverfassungsrechtlichen Regelungen (§7–§10) sind durch die
> Betriebsparteien auszufüllen.

## §1 Geltungsbereich

Diese Betriebsvereinbarung gilt für alle Arbeitnehmerinnen und
Arbeitnehmer der _[Firma]_ (im Folgenden "Unternehmen"), auf deren
Arbeitsgeräten der **Ant Observation Agent** (Desktop-Anwendung und/oder
Browser-Erweiterung) installiert wird.

## §2 Zweck

Der Ant Observation Agent dient ausschließlich dem Zweck, repetitive
mehrstufige Arbeitsabläufe zu identifizieren, die von **mindestens drei
Mitarbeitenden** regelmäßig durchgeführt werden, um diese Abläufe als
Kandidaten für eine spätere Automatisierung vorzuschlagen.

Die Verarbeitung dient **nicht**:
- der Leistungs- oder Verhaltenskontrolle einzelner Arbeitnehmer,
- als Grundlage für arbeitsrechtliche Maßnahmen,
- der individualisierten Berichterstattung an Vorgesetzte.

## §3 Umfang der Datenerhebung *(Auftragsverarbeiter-geliefert)*

### §3.1 Erfasste Kategorien

Die folgenden Metadaten werden erfasst und sind in der abschließenden
Tabelle in Anlage 1 (Privacy Notice, §2) aufgeführt:

- Anwendungswechsel (Quell- und Zielanwendung)
- Fensterfokus (Anwendung, Dauer in Millisekunden)
- Dateioperationen (Dateiname und Aktion: öffnen/speichern/schließen; **niemals** Dateiinhalt)
- Browser-Navigation (Host + Pfad-Template, IDs werden maskiert)
- Formular-Absendungen (Formular- und Feldnamen; **niemals** Feldwerte)
- Agent-Heartbeat

### §3.2 Ausdrücklich ausgeschlossen

Technisch ausgeschlossen sind (siehe `services/observation-ingest/src/privacy.py`):

- Tastatureingaben (Keylogging)
- Zwischenablage-Inhalte
- Formularfeldinhalte jeglicher Art
- Bildschirminhalte, Screenshots, Bildschirmaufzeichnungen
- Kamera- und Mikrofonaufnahmen
- Cookies, Session-Tokens, Authentifizierungsheader
- Dateiinhalte

Der Ingest-Dienst weist Ereignisse, die eine dieser Kategorien enthalten,
technisch zurück und erzeugt einen Sicherheitsalarm.

## §4 Pausenfunktion (Unterbrechung der Beobachtung)

Jede/r Arbeitnehmer/in hat jederzeit das Recht, die Beobachtung über
das Symbol des Ant Agents (System-Tray bzw. Browser-Toolbar) zu
unterbrechen. Die Unterbrechung:

- wirkt sofort,
- muss nicht begründet werden,
- darf keine arbeitsrechtlichen Konsequenzen haben,
- ist insbesondere während Pausenzeiten, Personalgesprächen, Betriebsrats-
  tätigkeit, Arztbesuchen und sonstigen nicht arbeitsbezogenen Nutzungen
  des Geräts zu aktivieren.

## §5 Aggregation und Schwellenwerte *(Auftragsverarbeiter-geliefert)*

Arbeitsablaufmuster werden nur dann in den Vorschlags-Katalog
aufgenommen, wenn sie von **mindestens drei** verschiedenen
Mitarbeitenden durchgeführt wurden (code-seitig erzwungen in
`services/pattern-classifier/src/constraints.py::MIN_EMPLOYEE_AGGREGATION = 3`).

Muster, die von weniger als drei Mitarbeitenden stammen, werden vor
dem Klassifikationsschritt verworfen und sind nicht rekonstruierbar.

## §6 Speicherdauer *(Auftragsverarbeiter-geliefert)*

| Datentyp | Speicherdauer |
| --- | --- |
| Roh-Beobachtungsdaten | 90 Tage |
| Aggregierte Muster (k≥3) | 365 Tage |
| Audit-Log der Vorschlagsentscheidungen | 3 Jahre |

Die Speicherdauer wird durch geplante Datenbankjobs technisch
erzwungen.

## §7 Einsicht, Auskunft, Berichtigung, Löschung

Jede/r Arbeitnehmer/in hat das Recht auf:

1. Auskunft über die zu ihrer/seiner Person gespeicherten
   Beobachtungsdaten gem. Art. 15 DS-GVO.
2. Berichtigung unrichtiger Daten gem. Art. 16 DS-GVO.
3. Löschung gem. Art. 17 DS-GVO, soweit keine gesetzlichen
   Aufbewahrungspflichten entgegenstehen.
4. Widerspruch gem. Art. 21 DS-GVO.

Anträge sind an die/den Datenschutzbeauftragte/n _[Kontakt]_ zu richten
und werden innerhalb von 30 Tagen beantwortet.

## §8 Mitbestimmungsrechte des Betriebsrats

Der Betriebsrat erhält:

- Lesezugriff auf die Liste der automatisch erkannten Workflow-
  Kandidaten **vor** deren Veröffentlichung an die Belegschaft.
- Vetorecht bei jedem Vorschlag, der nach Einschätzung des
  Betriebsrats zu Arbeitsverdichtung oder Abbau geschützter Tätigkeiten
  führen könnte.
- Quartalsweises Reporting über Anzahl erkannter Muster, Anzahl
  genehmigter/abgelehnter Vorschläge, Anzahl ausgeübter Pausen-
  funktionen (aggregiert, nicht personenbezogen).
- Sofortige Benachrichtigung bei jeder beabsichtigten Erweiterung
  des Beobachtungsumfangs.

## §9 Erweiterung des Beobachtungsumfangs

Jede Änderung an den in §3.1 genannten Kategorien erfordert:

1. Eine aktualisierte Datenschutz-Folgenabschätzung (DS-FA),
2. die erneute Zustimmung des Betriebsrats,
3. eine aktualisierte Fassung dieser Betriebsvereinbarung,
4. eine mindestens 14-tägige Ankündigungsfrist gegenüber der
   Belegschaft.

## §10 Inkrafttreten, Laufzeit, Kündigung

Diese Betriebsvereinbarung tritt am _[Datum]_ in Kraft. Sie kann von
jeder Betriebspartei mit einer Frist von drei Monaten zum Ende eines
Quartals gekündigt werden. Nach Kündigung gilt sie fort, bis eine neue
Betriebsvereinbarung abgeschlossen ist oder die Beobachtung eingestellt
wird.

Bei Kündigung wird der Ant Observation Agent innerhalb von 14 Tagen
deaktiviert und alle personenbezogenen Rohdaten werden gelöscht.

---

_[Ort, Datum]_

Für die Geschäftsleitung: _______________________

Für den Betriebsrat: _______________________

**Anlagen:**

1. Mitarbeitenden-Datenschutzhinweis ([employee-privacy-notice.md](employee-privacy-notice.md))
2. Datenschutz-Folgenabschätzung ([dpia-observation-layer.md](dpia-observation-layer.md))
3. Auftragsverarbeitungsvertrag mit Ant Automations B.V. *[gesondert]*
