# Instemmingsverzoek — Ant Observation Agent (NL)

> **Template — instemmingsverzoek aan de ondernemingsraad op grond van
> WOR art. 27 lid 1 sub l** (regelingen op het gebied van voorzieningen
> gericht op waarneming van of controle op aanwezigheid, gedrag of
> prestaties van de in de onderneming werkzame personen).
>
> Deze tekst is een model en MOET door de juridische afdeling van de
> klant worden aangepast voordat het aan de OR wordt voorgelegd. Ant
> Automations levert als verwerker het technische deel (§3, §5). De
> medezeggenschaps-procedurele onderdelen (§7–§9) vult de
> bestuurder/OR zelf in.

## 1. Aan

De ondernemingsraad van _[bedrijfsnaam]_.

## 2. Onderwerp

Het invoeren van de **Ant Observation Agent** (desktop-applicatie en/of
browser-extensie) op de werkplekken van de in de onderneming werkzame
personen, ten behoeve van het identificeren van repeterende
werkprocessen die voor automatisering in aanmerking komen.

## 3. Reikwijdte van de verwerking *(door verwerker geleverd)*

### 3.1 Wat wordt vastgelegd

- Applicatiewisselingen (bron- en doeltoepassing)
- Vensterfocus (toepassing, duur in milliseconden)
- Bestandsoperaties (bestandsnaam + actie: openen/opslaan/sluiten;
  **nooit** bestandsinhoud)
- Browser-navigatie (host + pad-template, ID's worden gemaskeerd)
- Formulierinzending (formulier- en veldnamen; **nooit** veldwaarden)
- Agent-heartbeat

### 3.2 Wat nadrukkelijk NIET wordt vastgelegd

Technisch uitgesloten (zie `services/observation-ingest/src/privacy.py`):

- Toetsaanslagen (keylogging)
- Inhoud van het klembord
- Waarden van formuliervelden (inclusief wachtwoorden, e-mail,
  vrije tekst)
- Schermafbeeldingen, schermopnames, DOM-snapshots
- Camera- of microfoon-opnames
- Cookies, sessietokens, authenticatie-headers
- Bestandsinhouden

## 4. Doel van de verwerking

Het uitsluitende doel is het herkennen van repeterende
werkprocessen die door **ten minste drie medewerkers** worden uitgevoerd,
zodat deze processen als automatiseringskandidaten kunnen worden
voorgesteld aan de OR en de belanghebbende medewerkers.

De verwerking wordt **niet** gebruikt voor:

- Individuele prestatiebeoordeling.
- Disciplinaire maatregelen.
- Individuele rapportage aan leidinggevenden.

## 5. Technische en organisatorische waarborgen *(door verwerker geleverd)*

1. **Aggregatiedrempel k≥3** — patronen van minder dan drie medewerkers
   worden automatisch verworpen
   (`services/pattern-classifier/src/constraints.py::MIN_EMPLOYEE_AGGREGATION = 3`).
2. **Inhoudsveld-blacklist** — de ingest-dienst weigert elke payload
   met verboden veldnamen en genereert een security-alert.
3. **Gesplitste bewaartermijnen** — rauwe observatiedata max. 90 dagen,
   aggregaten max. 365 dagen.
4. **Pauzeknop** — iedere medewerker kan observatie op elk moment
   stopzetten via het systeemvak-icoon; pauze mag niet tot disciplinaire
   maatregelen leiden.
5. **Schema-isolatie** — observatietabellen staan in een apart Postgres-
   schema; executieservices kunnen ze niet per abuis bevragen.

## 6. Rechtsgrond (AVG art. 6 & UAVG)

_[Kiezen en motiveren:]_

- [ ] Instemming OR ex art. 27 lid 1 sub l WOR, gekoppeld aan
      gerechtvaardigd belang ex AVG art. 6 lid 1 sub f.
- [ ] Wettelijke verplichting (specificeren).
- [ ] Uitvoering arbeidsovereenkomst (enkel voor nauw omschreven rollen).

Individuele toestemming van medewerkers is in een gezagsrelatie géén
geldige grondslag en wordt dus niet gebruikt.

## 7. Bewaartermijnen

| Gegevenstype | Bewaartermijn |
| --- | --- |
| Rauwe observatie-events | 90 dagen |
| Aggregaten (k≥3) | 365 dagen |
| Audit-log van voorstelbeslissingen | 3 jaar |

## 8. Rechten van medewerkers (AVG hoofdstuk III)

Medewerkers kunnen bij de Functionaris Gegevensbescherming verzoeken om:

- Inzage (art. 15)
- Rectificatie (art. 16)
- Verwijdering (art. 17)
- Beperking (art. 18)
- Dataportabiliteit (art. 20)
- Bezwaar (art. 21)

Verzoeken worden binnen 30 dagen afgehandeld. Klachten kunnen worden
ingediend bij de Autoriteit Persoonsgegevens.

## 9. Medezeggenschap

- De OR ontvangt **vóór publicatie aan de belegschaft** de lijst met
  automatisch herkende workflow-kandidaten.
- De OR heeft vetorecht op elk voorstel dat naar zijn oordeel tot
  werkdrukverhoging of afbouw van beschermde taken kan leiden.
- De OR ontvangt per kwartaal een geanonimiseerd rapport
  (aantal gevonden patronen, aantal goedgekeurd/afgewezen, aantal
  pauzes).
- Iedere voorgenomen uitbreiding van de observatiescope (zie §3) vereist
  een nieuw instemmingsverzoek.

## 10. Verzoek

De bestuurder verzoekt de OR om instemming met het invoeren van de Ant
Observation Agent onder de in dit verzoek beschreven voorwaarden, conform
WOR art. 27 lid 1 sub l.

_[Plaats, datum]_

De bestuurder: _______________________

**Bijlagen:**

1. Privacyverklaring medewerkers ([employee-privacy-notice.md](employee-privacy-notice.md))
2. DPIA ([dpia-observation-layer.md](dpia-observation-layer.md))
3. Verwerkersovereenkomst met Ant Automations B.V. *[apart]*
