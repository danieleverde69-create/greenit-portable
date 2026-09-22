# Green IT - avvio web locale

Gli avviatori risolvono i percorsi rispetto alla directory dell'SSD e avviano
il servizio dati (`8174`) e la vista web Vinext (`3000`).

Per una distribuzione completamente portable, aggiungere i runtime nelle
cartelle `runtime/<sistema>-<architettura>/`:

- `greenit-service` compilato con PyInstaller (oppure `python` con il pacchetto `cryptography` incluso);
- `node` con `node_modules` pronto nel progetto. Il launcher usa direttamente
  `vinext start`; Wrangler/workerd servono solo per il deploy Cloudflare.

I file nella radice `GreenIT-macOS.command`, `GreenIT-Windows.bat`,
`GreenIT-Linux.sh` e `GreenIT.desktop` sono gli avviatori cliccabili per i tre
sistemi. Prima della consegna va eseguita una build web con
`npm run build`.

## Creazione di un pacchetto

Dopo aver preparato `runtime/<piattaforma>/greenit-service` e
`runtime/<piattaforma>/node`, dalla directory principale eseguire:

```text
python3 portable/package.py darwin-arm64
python3 portable/package.py darwin-x64
python3 portable/package.py linux-x64
python3 portable/package.py windows-x64
```

Il risultato viene scritto in `release/GreenIT-<piattaforma>.zip`. Gli archivi
hanno tutti la stessa radice interna `GreenIT/`: se vuoi usare l'SSD su piu'
sistemi, estrai gli archivi nella stessa cartella e conserva una sola cartella
`data/`. I launcher useranno automaticamente quel database condiviso.
