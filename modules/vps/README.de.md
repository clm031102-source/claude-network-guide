# Claude Network Guide · VPS

> Independent source reference for the advanced VPS component. No tutorial site is currently hosted by this repository. Start with the [main tutorial and local workbench](../../README.md); source attribution is preserved in [NOTICE](../../NOTICE.md).

[中文](./README.md) · [English](./README.en.md) · [한국어](./README.ko.md) · [日本語](./README.ja.md) · [العربية](./README.ar.md) · [Español](./README.es.md) · [Français](./README.fr.md) · [Русский](./README.ru.md) · **Deutsch** · [Português](./README.pt.md)

Geschäftsreise in ein Land, in dem das Internet schwer nutzbar ist? Nutzen Sie Ihre gewohnten Websites und KI-Tools einfach weiter.

Quellcode der Tutorial-Website, noch nicht veröffentlicht: [Chinesisch](site/src/pages/) · [Englisch](site/src/pages/en/) · [lokale Vorschau](site/README.md). GitHub zeigt nur den Quellcode.

So geht's: Sie kaufen einen eigenen Server im Ausland, lassen ihn von einer KI mit diesem Projekt einrichten und importieren ein Abo auf Handy und Computer. Die Verbindung gehört nur Ihnen und wird nicht mit Fremden geteilt.

## Was Sie bekommen

- **Ihre eigene Verbindung** für Computer, Handy und Router. Es gibt einen Haupt- und einen Reserveknoten: Fällt einer aus, wird automatisch auf den anderen umgeschaltet.
- **Sofort nutzbar nach dem Import.** Regeln für gängige Websites und KI-Tools sind schon eingerichtet. Websites aus Festlandchina werden direkt verbunden, alles andere läuft über Ihren Server.
- **CLIProxyAPI**: Ihr eigener API-Zugang mit Verwaltungsoberfläche, der sich automatisch auf die neueste Version aktualisiert.
  - ⚠️ **Verbinden Sie kein Claude-Konto mit CLIProxyAPI**: Die Richtlinien von Anthropic erlauben das nicht. OpenAI hat erklärt, dass ChatGPT-Konten so genutzt werden dürfen – ich nutze das selbst sehr gern zum Erstellen von Bildern.
- **Sicher**: Der Server akzeptiert nur den Schlüssel auf Ihrem Computer und nutzt ein echtes HTTPS-Zertifikat, der Browser warnt also nie mit „nicht sicher“.
- **Kaum Wartung**: Zertifikate, Regeln und CLIProxyAPI aktualisieren sich selbst, die Konfiguration wird täglich gesichert.

## Drei Schritte

### 1. Server kaufen

Nehmen Sie derzeit **BandwagonHost**. Das Netz ist stabil, und ich nutze es selbst:

**[BandwagonHost kaufen](https://bandwagonhost.com/)**

Der Tarif hinter diesem Link enthält **1 TB Datenvolumen pro Monat** – genug für Sie und Ihre Familie.

[DMIT](https://www.dmit.io/) ist auch gut, aber im Moment ausverkauft. Warten lohnt sich nicht.

> Beides sind meine Empfehlungslinks. Wenn Sie darüber kaufen, erhalte ich unter Umständen eine Provision; diese Einnahmen verwende ich für wohltätige Zwecke. Preise und Verfügbarkeit laut den offiziellen Websites.

Wählen Sie **Ubuntu 24.04** als System. Sobald der Server bereit ist, notieren Sie aus dem Kundenbereich drei Dinge: **Server-IP, root-Passwort (oder Schlüsseldatei) und SSH-Port**.

### 2. Von einer KI einrichten lassen

Öffnen Sie ein KI-Tool, das Befehle auf Ihrem Computer ausführen kann, etwa [Codex](https://github.com/openai/codex) oder [Claude Code](https://claude.com/claude-code) (unter Windows in WSL). Kopieren Sie den Text unten, füllen Sie ihn aus und senden Sie ihn ab:

```text
Bitte richte meinen neuen Server nach dem Plan „claude-network-guide“ ein.

Plan: https://github.com/clm031102-source/claude-network-guide
Lade dieses Projekt zuerst auf meinen Computer und lies
modules/vps/skills/claude-network-guide/SKILL.md vollständig. Halte dich genau an die
Schritte und Regeln dort und nutze die Skripte des Projekts für Einrichtung
und Prüfung. Bitte sprich mit mir auf Deutsch.

Mein Server:
- IP:
- Anmeldung: Startpasswort (lass es mich selbst im Terminal eingeben)
- SSH-Benutzer und Port: Standard
- Name, mit dem ich mich künftig anmelden will: bwg
```

Nur drei Stellen müssen Sie ändern:

- **IP**: die Server-IP aus dem Kundenbereich.
- **Anmeldung**: Wenn Ihr Anbieter eine Schlüsseldatei mitgegeben hat, ersetzen Sie es durch `Schlüsseldatei: Pfad zur Datei` (ein Zip geht auch).
- **Name**: Ersetzen Sie `bwg` durch einen beliebigen Namen. Danach genügt `ssh dieser-name`, um sich am Server anzumelden.

Wenn Benutzer und Port nicht root / 22 sind, ersetzen Sie „Standard“ durch die echten Werte.

Dann warten Sie, bis die KI fertig ist, meist 10–20 Minuten. Zwischendurch bittet sie Sie einmal, das Server-Passwort im Terminal einzugeben. **Fügen Sie das Passwort nie in den Chat ein.** Nach der Einrichtung ist die Passwort-Anmeldung abgeschaltet; anmelden kann sich nur noch dieser Computer.

Kann die KI das Projekt nicht herunterladen, [laden Sie das ZIP](https://github.com/clm031102-source/claude-network-guide/archive/refs/heads/main.zip) selbst herunter, entpacken Sie es und ergänzen Sie den Text um die Zeile: „Das Projekt liegt bereits hier: Ordnerpfad“.

Danach liegt auf Ihrem Schreibtisch die Datei `my-server-ihr-name-subscriptions-and-accounts-de.md` mit:

- der **Clash-Abo-URL** für Computer und Router und der **Shadowrocket-Abo-URL** fürs iPhone;
- Adresse, Benutzername und Passwort des 3x-ui-Panels;
- Adresse der CLIProxyAPI-Verwaltung, deren Anmeldeschlüssel, API-Adresse und API-Schlüssel.

<details>
<summary>Richten Sie öfter Server ein? Als Skill installieren und mit einem Satz aufrufen</summary>

Einmal im Terminal ausführen:

```bash
git clone https://github.com/clm031102-source/claude-network-guide.git
mkdir -p ~/.claude/skills ~/.codex/skills
cp -R claude-network-guide/modules/vps/skills/claude-network-guide ~/.claude/skills/
cp -R claude-network-guide/modules/vps/skills/claude-network-guide ~/.codex/skills/
```

Danach genügt es, der KI „richte meinen neuen Server mit claude-network-guide ein“ zu sagen; die nötigen Angaben fragt sie selbst ab.

</details>

### 3. Abo importieren

- **Computer (empfohlen: Clash Verge Rev)**: [Clash Verge Rev](https://github.com/clash-verge-rev/clash-verge-rev/releases) installieren, die Clash-Abo-URL importieren, den Modus **Regel (Rule)** wählen und den **TUN-Modus** (virtuelle Netzwerkkarte; bei Nachfrage den Dienst installieren) einschalten. Mit nur dem System-Proxy kann WebRTC im Browser Ihre echte IP verraten – siehe die [Anleitung gegen WebRTC-Lecks](./docs/Clash-Verge-WebRTC泄露修复手册.md) (auf Chinesisch, so geschrieben, dass ein KI-Assistent sie Schritt für Schritt befolgen kann).
- **iPhone**: die Shadowrocket-Abo-URL in Shadowrocket importieren.
- **Router (OpenClash)**: dieselbe Clash-Abo-URL funktioniert, so nutzen alle Geräte zu Hause die Leitung. Unter Konfigurations-Abo hinzufügen (die YAML-Datei nicht hochladen, sonst fehlt die Verbrauchsanzeige und die Regeln aktualisieren sich nicht), die Online-Abo-Konvertierung ausschalten und den Meta-Kern verwenden.
- **Sie nutzen bereits v2rayN (Windows / Mac / Linux)**: funktioniert, aber nur als Ausweichlösung. Importieren Sie die Abo-URL aus der Zeile „Shadowrocket (iPhone)“ (nicht die Clash-Zeile), wählen Sie das Routing „Festlandchina umgehen“ und schalten Sie TUN gegen WebRTC-Lecks ein. Dieses Abo enthält nur die Knoten, ohne KI-Routing und WeChat-Direktregeln – deshalb bleibt Clash Verge Rev die Empfehlung am Computer. Siehe [v2rayN-Anleitung](https://github.com/clm031102-source/claude-network-guide/blob/main/modules/vps/site/src/pages/en/howto/v2rayn.mdx) (Englisch).

Öffnen Sie dann <https://ip.net.coffee/claude/>. Wird die IP Ihres Servers angezeigt, sind Sie verbunden.

## Vor der Reise

- **Richten Sie alles vor der Abreise ein und testen Sie es.** In einem eingeschränkten Netz kann schon das Herunterladen des Projekts oder das Öffnen von KI-Tools viel schwieriger werden.
- Installieren Sie die Clients und importieren Sie die Abos auf Handy und Computer, und prüfen Sie, ob beide Knoten verbinden.
- Erreicht ein lokales Netz Ihren Server nicht, probieren Sie zuerst ein anderes (Hotel-WLAN, mobile Daten, anderer Anbieter). Geht gar nichts, ist die Server-IP dort vermutlich gesperrt. Das lässt sich nicht per Konfiguration beheben; bitten Sie Ihren Anbieter um eine neue IP.
- Nutzen Sie die Verbindung nur selbst und mit Ihrer Familie. Geben Sie sie nicht weiter.

## Server später prüfen

Senden Sie der KI diesen Text (ersetzen Sie `bwg` durch Ihren Namen):

```text
Bitte prüfe meinen Server nach dem Plan „claude-network-guide“: ssh bwg

Plan: https://github.com/clm031102-source/claude-network-guide
Lade das Projekt herunter und lies den Teil „以后的复核和维护“ (spätere
Prüfung und Wartung) in modules/vps/skills/claude-network-guide/SKILL.md.
Prüfe zuerst nur, sag mir, was fehlgeschlagen ist und warum, und repariere erst, wenn ich zustimme.
Zeige keine Passwörter, Abo-URLs oder Schlüssel im Chat. Bitte sprich mit mir auf Deutsch.
```

Die ausführliche Dokumentation ([Fehlerbehebung](./skills/claude-network-guide/references/troubleshooting.md), [Aufbau im Detail](./skills/claude-network-guide/references/design.md)) gibt es derzeit nur auf Chinesisch; Ihre KI kann sie für Sie lesen.

## Feedback und Vorschläge



## Datenschutz

- Dieses Projekt enthält keinerlei Informationen über echte Server.
- Passwörter, Schlüssel, Abo-URLs und API-Schlüssel jedes Servers werden bei der Einrichtung neu erzeugt und nur auf dem Server und Ihrem Computer gespeichert. Die KI zeigt sie nicht im Chat.
- Veröffentlichen Sie Ihre Zugangsdatei, Abo-URLs und Schlüssel nirgends und machen Sie keine Screenshots davon.
- Sicherheitsprobleme melden Sie bitte gemäß [SECURITY.md](./SECURITY.md).

Ob und wie schnell Sie sich verbinden können, hängt auch vom lokalen Netz und vom Routing des Servers ab. Dieses Projekt sorgt dafür, dass der Server richtig eingerichtet ist, kann aber nicht garantieren, dass dieselbe IP aus jedem Land und von jedem Anbieter erreichbar ist.

## Lizenz

[MIT](./LICENSE)
