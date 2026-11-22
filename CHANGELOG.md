# Changelog

Alle wichtigen Änderungen am Blueprint. Die Versionen folgen [Semantic Versioning](https://semver.org/lang/de/).

## 1.1.0 – unveröffentlicht

### Geändert

- **Die Wartezeit übersteht Neustarts.** Statt eines Zustandsauslösers mit `for:` (den Home Assistant bei jedem Neustart zurücksetzt) sucht die Automation alle 15 Minuten nach Updates, deren Wartezeit abgelaufen ist. Ein Neustart während der Wartezeit lässt die Prüfung nicht mehr ausfallen; für Updates, die noch offen sind, beginnt die Wartezeit von vorn.
- Automatische Läufe gibt es nur, wenn etwas fällig ist. Leere Takte hinterlassen keine Spuren und ändern „zuletzt ausgelöst“ nicht.

### Neu

- Optionale Eingabe **Remember checked versions**: ein Text-Helfer, in dem sich die Automation die geprüften Versionen merkt. Damit führen Neustarts nie zu einer zweiten Prüfung derselben Version, und eine neuere Version, die eine noch offene ersetzt, wird ebenfalls geprüft.
- Versionsnummer in der Beschreibung des Blueprints und in diesem Changelog.
- Laufzeittests, die den Blueprint in einer echten Testinstanz von Home Assistant ausführen (Wartezeit, Neustart, Gedächtnis, Start von Hand, Fehlertext).

## 1.0.0 – 2026-10-25

Erste Version: Grok prüft ein offenes Update nach einer einstellbaren Wartezeit und schickt eine Einschätzung (Install / Wait / Caution) mit bis zu drei gemeldeten Problemen aufs Handy und auf Wunsch die vollständige Antwort mit Quellen als Benachrichtigung in Home Assistant. Ein Start von Hand prüft alle offenen Updates.
