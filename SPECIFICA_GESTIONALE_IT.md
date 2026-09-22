# Gestionale IT Locale — Specifica operativa v1.0

## 1. Obiettivo

Applicazione **local-first** per un IT Manager che gestisce più aziende. Centralizza in modo sicuro credenziali, accessi, documentazione tecnica, ticket, scadenze, contratti, reti e backup. Non usa servizi cloud per archiviare dati: l'unica connessione esterna opzionale è Gmail SMTP per l'invio delle notifiche.

La priorità del prodotto è il vault delle credenziali multi-azienda; l'inventario degli asset resta intenzionalmente essenziale nella prima versione.

## 2. Modalità di esecuzione

- Web app locale aperta nel browser, inizialmente solo su `localhost`.
- Installazione guidata per macOS, Windows e Linux.
- Avvio automatico all'accensione della macchina ospitante.
- Estensione futura: accesso controllato dalla rete locale per i membri del team.
- Lingua iniziale italiana; struttura pronta per la traduzione in inglese.
- Tema chiaro e scuro.

## 3. Sicurezza

### Accesso e dati sensibili

- Master password obbligatoria alla prima configurazione.
- Le password, i segreti TOTP, le chiavi API e i codici di recupero sono cifrati localmente; non sono mai memorizzati né registrati in chiaro.
- Chiave di recupero offline generata durante il setup, da stampare e salvare su chiavetta USB.
- TOTP per l'accesso applicativo disponibile come opzione.
- Blocco automatico dopo **15 minuti** di inattività.
- Gli appunti vengono svuotati **60 secondi** dopo la copia di una password.
- Nessuna password, codice di recupero o segreto viene incluso in email, report o log.

### Tracciabilità e recupero

- Storico cifrato delle modifiche alle credenziali.
- Audit log locale: accessi, visualizzazioni/copie/modifiche delle credenziali, eliminazioni, backup e ripristini.
- Conservazione audit log: **3 anni**.
- Cestino recuperabile per elementi cancellati: **90 giorni**.
- Aziende terminate archiviate, non eliminate: i dati restano consultabili ma non compaiono nella vista operativa.

## 4. Organizzazione dei dati

Ogni dato operativo appartiene a una singola azienda o all'area interna. I file avranno cartelle separate per azienda; nel database i record sono isolati da un identificativo azienda.

```text
Archivio dati scelto in installazione/
  database/
  aziende/
    <azienda-id>/
      documenti/
      vault-obsidian/
      diagrammi/
      allegati-ticket/
  gestione-interna/
  backup-temporanei/
  audit/
```

Le aziende possono avere più sedi. Ogni sede può avere contatti, infrastruttura, documenti e asset propri.

## 5. Moduli funzionali

### Dashboard e ricerca

- Vista aggregata di tutte le aziende e vista filtrata dell'azienda attiva.
- Widget configurabili e riordinabili: ticket aperti, scadenze imminenti, attività ricorrenti, backup più recente, errori, costi e ore registrate.
- Barra laterale fissa con selettore dell'azienda sempre visibile.
- Ricerca globale per aziende, contatti, credenziali, documenti, note, ticket e scadenze. Le password non vengono indicizzate né esposte dalla ricerca.
- Scorciatoie: ricerca, nuova credenziale, nuovo ticket e blocco immediato.

### Aziende, sedi, contatti e fornitori

- Anagrafica azienda: ragione sociale, P. IVA/codice fiscale, sedi, referenti, contatti, note e documenti.
- Rubrica di dipendenti, amministratori e contatti tecnici; associazione agli account e agli accessi di cui sono responsabili.
- Rubrica fornitori: ISP, hosting, software house e partner; collegamenti a contratti, servizi, ticket e credenziali.
- Area `Personale / Gestione interna` per elementi non riferiti a un cliente.

### Vault credenziali e accessi

- Categorie: cloud, amministrativi, Wi-Fi, VPN, server, applicativi, email, condivise e personalizzate.
- Campi: titolo, servizio/URL, utente, password, note, titolare, referenti, tag, data modifica, data revisione/scadenza, codici recovery, chiavi API e segreti TOTP.
- Generatore di password robuste e controllo di password deboli, duplicate o non revisionate.
- Versioni precedenti delle password mantenute in forma cifrata.
- Copia sicura negli appunti e apertura di URL, percorsi, RDP o SSH tramite collegamenti. Non viene incluso un client remoto nella v1.
- Esportazione solo in archivio cifrato di emergenza.

### Procedure e knowledge base Obsidian

- Creazione automatica di un vault Obsidian locale, con cartelle separate per azienda.
- Note Markdown modificabili sia dal gestionale sia direttamente in Obsidian.
- Procedure, checklist, configurazioni di rete, accessi di emergenza e istruzioni operative.
- Supporto di titoli, elenchi, tabelle, collegamenti, immagini e allegati.

### Ticket, attività e checklist

- Ticket associati a un'azienda, a una sede e, se utile, a un servizio o asset.
- Priorità, stato personalizzabile, scadenza, descrizione, note, allegati, attività e storico.
- Registrazione del tempo; tariffa e totale economico opzionali.
- Ticket ricorrenti creati automaticamente dalle attività pianificate, con promemoria email.
- Checklist riutilizzabili: onboarding, offboarding, configurazione PC, rinnovi e controlli backup.
- Checklist di onboarding/offboarding con account, licenze, dispositivi e rotazione credenziali.
- Report d'intervento in PDF per ticket chiusi, privo di segreti.
- I ticket vengono creati manualmente nella v1; l'acquisizione da email resta una possibile evoluzione.

### Scadenze, contratti e costi

- Domini, SSL, licenze, garanzie, manutenzioni, contratti, hosting, connettività, Microsoft 365/Google Workspace e altri servizi.
- Date di rinnovo, periodicità, importi, imponibile/IVA, documenti, fatture e pagamenti.
- Valuta predefinita: EUR.
- Avvisi configurabili per scadenza, con default a 30, 15, 7 e 1 giorno prima.
- Calendario unico di ticket, attività, rinnovi e scadenze.
- Report PDF ed Excel: costi, ticket/ore, scadenze, asset e backup; eventuali report credenziali escludono sempre le password.

### Infrastruttura e asset

- Registro essenziale per PC, notebook, server, monitor, stampanti, apparati di rete, telefoni, VM e dispositivi mobili.
- Associazione dell'asset a sede, utente, stato, seriale, acquisto/garanzia e documenti.
- Documentazione di rete: subnet, IP, gateway, DNS, VLAN, firewall, VPN e Wi-Fi.
- Editor integrato per topologie modificabili; importazione di diagrammi, immagini e PDF.
- Campi personalizzati, estendibili in futuro senza modificare il software.

## 6. Email e notifiche

- Account Gmail unico configurato tramite password per app.
- Destinatari configurabili per azienda, anche multipli in futuro.
- Avvisi per scadenze, ticket, attività ricorrenti, backup riusciti o falliti e destinazioni non disponibili.
- Riepilogo per tutte le aziende ogni lunedì alle **09:00**.
- Il corpo delle email contiene solo azienda, tipo di evento, priorità/data e riferimento interno.

## 7. Backup e ripristino

- Backup completo di database, vault cifrato, allegati, documenti, diagrammi e vault Obsidian.
- Esecuzione automatica **dal lunedì al venerdì alle 21:30**; se la macchina è spenta, recupero alla successiva apertura dell'app.
- Avvio manuale sempre disponibile.
- Destinazioni multiple simultanee: cartella locale, USB e NAS.
- Archivi compressi e cifrati; verifica di integrità prima del salvataggio.
- Conservazione degli **ultimi 7 backup complessivi** per destinazione.
- Backup automatico prima di ogni aggiornamento dell'app.
- Procedura guidata per ispezione e ripristino.
- Test pianificato di ripristino ogni **tre mesi**.

## 8. Modello dati essenziale

| Entità | Relazioni principali |
| --- | --- |
| Azienda | sedi, contatti, fornitori, servizi, credenziali, ticket, documenti |
| Sede | azienda, rete, asset, contatti, ticket |
| Credenziale | azienda/area interna, servizio, contatti, storico, tag |
| Servizio/contratto | azienda, fornitore, scadenze, costi, fatture, credenziali |
| Ticket | azienda, sede, asset/servizio, attività, checklist, tempi, allegati |
| Procedura | azienda/area interna, file Markdown Obsidian, tag, allegati |
| Rete | azienda/sede, subnet, IP, apparati, diagrammi |
| Backup | destinazione, archivio, esito, integrità, audit |

## 9. Architettura proposta

- **Backend:** Python/FastAPI, API locale e pianificatore di attività.
- **Interfaccia:** React, eseguita dal browser contro il servizio locale.
- **Database:** SQLite per l'installazione singola; progettazione compatibile con PostgreSQL per un eventuale server LAN multiutente.
- **Cifratura:** chiavi derivate dalla master password, cifratura autenticata per i segreti; file e backup cifrati localmente.
- **Archivio file:** cartelle locali organizzate per azienda, gestite dal programma.
- **Obsidian:** Markdown su filesystem, senza dipendenza dal database per la lettura delle note.

## 10. Piano di rilascio

1. **Fondazione sicura:** installazione, master password/recupero, aziende/sedi/contatti, vault credenziali, documenti, audit e backup.
2. **Operatività quotidiana:** dashboard, scadenze, contratti/costi, ticket, ore, checklist, calendario, Gmail e report.
3. **Documentazione infrastrutturale:** Obsidian, reti/IP, diagrammi, asset essenziali, fornitori e fatture.
4. **Evoluzioni:** utenti del team in LAN, monitoraggio attivo, ticket via email e database PostgreSQL centralizzato.

## 11. Criteri di accettazione del primo rilascio

- È possibile creare due aziende e verificare che documenti, vault e ricerche restino separati.
- Una credenziale è salvata, visualizzata e copiata senza comparire in chiaro nei log o nella ricerca.
- Il blocco dopo 15 minuti e lo svuotamento appunti dopo 60 secondi funzionano.
- Un ticket genera un promemoria e registra ore/checklist.
- Un backup cifrato parte alle 21:30 nei giorni lavorativi, viene verificato e conserva solo le ultime sette copie.
- Il ripristino guidato recupera un archivio completo in una posizione sicura.
- Gli avvisi Gmail non includono segreti e vengono inviati ai destinatari dell'azienda corretta.
