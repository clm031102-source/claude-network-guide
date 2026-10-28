# Claude Network Guide · VPS

> Independent source reference for the advanced VPS component. No tutorial site is currently hosted by this repository. Start with the [main tutorial and local workbench](../../README.md); source attribution is preserved in [NOTICE](../../NOTICE.md).

[中文](./README.md) · [English](./README.en.md) · [한국어](./README.ko.md) · [日本語](./README.ja.md) · [العربية](./README.ar.md) · [Español](./README.es.md) · **Français** · [Русский](./README.ru.md) · [Deutsch](./README.de.md) · [Português](./README.pt.md)

Vous partez dans un pays où internet est difficile d'accès ? Continuez à utiliser vos sites et vos outils d'IA habituels.

Sources du site de tutoriel, non déployé : [chinois](site/src/pages/) · [anglais](site/src/pages/en/) · [aperçu local](site/README.md). Les dossiers GitHub ne font pas fonctionner le site.

Le principe : vous achetez votre propre serveur à l'étranger, une IA le configure avec ce projet, puis vous importez un abonnement sur votre téléphone et votre ordinateur. La connexion est à vous seul, sans la partager avec des inconnus.

## Ce que vous obtenez

- **Votre propre connexion** pour ordinateur, téléphone et routeur. Un nœud principal et un nœud de secours : si l'un tombe, l'autre prend le relais automatiquement.
- **Prêt dès l'import.** Les règles pour les sites et outils d'IA courants sont déjà en place. Les sites de Chine continentale se connectent directement ; tout le reste passe par votre serveur.
- **CLIProxyAPI** : votre propre point d'accès API et son panneau d'administration, mis à jour automatiquement vers la dernière version.
  - ⚠️ **Ne connectez pas de compte Claude à CLIProxyAPI** : la politique d'Anthropic ne l'autorise pas. OpenAI a indiqué que les comptes ChatGPT peuvent être utilisés ainsi — personnellement, j'adore m'en servir pour créer des images.
- **Sécurisé** : le serveur n'accepte que la clé de votre ordinateur et utilise un vrai certificat HTTPS, donc pas d'avertissement « non sécurisé » dans le navigateur.
- **Presque aucun entretien** : certificats, règles et CLIProxyAPI se mettent à jour tout seuls, et la configuration est sauvegardée chaque jour.

## Trois étapes

### 1. Achetez un serveur

En ce moment, prenez **BandwagonHost**. Le réseau est stable, c'est celui que j'utilise moi-même :

**[Acheter BandwagonHost](https://bandwagonhost.com/)**

L'offre de ce lien inclut **1 To de trafic par mois**, largement assez pour vous et votre famille.

[DMIT](https://www.dmit.io/) est bien aussi, mais il est en rupture de stock. Inutile d'attendre.

> Ce sont mes deux liens de parrainage. Je peux toucher une commission si vous achetez par leur biais, et je consacrerai ce revenu à des actions caritatives. Prix et disponibilité selon les sites officiels.

Choisissez **Ubuntu 24.04** comme système. Une fois le serveur prêt, notez trois informations dans le panneau : **IP du serveur, mot de passe root (ou fichier de clé) et port SSH**.

### 2. Laissez une IA le configurer

Ouvrez un outil d'IA capable d'exécuter des commandes sur votre ordinateur, comme [Codex](https://github.com/openai/codex) ou [Claude Code](https://claude.com/claude-code) (sous Windows, utilisez-le dans WSL). Copiez le texte ci-dessous, complétez-le et envoyez-le :

```text
Merci de configurer mon nouveau serveur selon le plan « claude-network-guide ».

Plan : https://github.com/clm031102-source/claude-network-guide
Téléchargez d'abord ce projet sur mon ordinateur et lisez entièrement
modules/vps/skills/claude-network-guide/SKILL.md. Suivez exactement ses étapes et ses règles,
et utilisez les scripts du projet pour la configuration et la vérification.
Parlez-moi en français, s'il vous plaît.

Mon serveur :
- IP :
- Connexion : mot de passe initial (laissez-moi le saisir moi-même dans le terminal)
- Utilisateur et port SSH : par défaut
- Nom que je veux utiliser pour me connecter : bwg
```

Il n'y a que trois choses à changer :

- **IP** : l'IP du serveur indiquée dans le panneau.
- **Connexion** : si votre fournisseur vous a donné un fichier de clé, remplacez par `fichier de clé : chemin du fichier` (un zip convient).
- **Nom** : remplacez `bwg` par le nom de votre choix. Ensuite, il suffit de taper `ssh ce-nom` pour entrer sur le serveur.

Si l'utilisateur et le port ne sont pas root / 22, remplacez « par défaut » par les vraies valeurs.

Attendez ensuite que l'IA termine, en général 10 à 20 minutes. À un moment, elle vous demandera de saisir le mot de passe du serveur dans le terminal. **Ne collez jamais le mot de passe dans la discussion.** Une fois terminé, la connexion par mot de passe est désactivée et seul cet ordinateur peut se connecter.

Si l'IA n'arrive pas à télécharger le projet, [téléchargez le ZIP](https://github.com/clm031102-source/claude-network-guide/archive/refs/heads/main.zip) vous-même, décompressez-le et ajoutez une ligne au texte : « Le projet se trouve déjà ici : chemin du dossier ».

À la fin, un fichier `my-server-votre-nom-subscriptions-and-accounts-fr.md` apparaît sur votre bureau, avec :

- l'**URL d'abonnement Clash** pour ordinateur et routeur, et l'**URL d'abonnement Shadowrocket** pour iPhone ;
- l'adresse, l'utilisateur et le mot de passe du panneau 3x-ui ;
- l'adresse du panneau CLIProxyAPI, sa clé de connexion, l'adresse de l'API et la clé API.

<details>
<summary>Vous configurez souvent des serveurs ? Installez-le comme skill et appelez-le en une phrase</summary>

À exécuter une fois dans le terminal :

```bash
git clone https://github.com/clm031102-source/claude-network-guide.git
mkdir -p ~/.claude/skills ~/.codex/skills
cp -R claude-network-guide/modules/vps/skills/claude-network-guide ~/.claude/skills/
cp -R claude-network-guide/modules/vps/skills/claude-network-guide ~/.codex/skills/
```

Ensuite, il suffit de dire à l'IA « utilise claude-network-guide pour configurer mon nouveau serveur » et elle vous demandera les informations.

</details>

### 3. Importez l'abonnement

- **Ordinateur (recommandé : Clash Verge Rev)** : installez [Clash Verge Rev](https://github.com/clash-verge-rev/clash-verge-rev/releases), importez l'URL d'abonnement Clash, choisissez le mode **Règles (Rule)** et activez le **mode TUN** (carte réseau virtuelle ; installez le service si on vous le demande). Avec le seul proxy système, le WebRTC du navigateur peut révéler votre vraie IP : voir le [guide de correction des fuites WebRTC](./docs/Clash-Verge-WebRTC泄露修复手册.md) (en chinois, rédigé pour qu'un assistant IA puisse le suivre pas à pas).
- **iPhone** : importez l'URL d'abonnement Shadowrocket dans Shadowrocket.
- **Routeur (OpenClash)** : la même URL d'abonnement Clash fonctionne, tous les appareils de la maison passent par la ligne. Ajoutez-la dans l'abonnement de configuration (n'importez pas le fichier YAML, sinon la consommation ne s'affiche pas et les règles ne se mettent pas à jour), désactivez la conversion d'abonnement en ligne et utilisez le cœur Meta.
- **Vous utilisez déjà v2rayN (Windows / Mac / Linux)** : ça fonctionne, mais seulement en solution de repli. Importez l'URL de la ligne « Shadowrocket (iPhone) » (pas celle de Clash), choisissez le routage « contourner la Chine continentale » et activez TUN contre les fuites WebRTC. Cet abonnement ne contient que les nœuds, sans les règles IA ni WeChat en direct : sur ordinateur, Clash Verge Rev reste recommandé. Voir le [guide v2rayN](https://github.com/clm031102-source/claude-network-guide/blob/main/modules/vps/site/src/pages/en/howto/v2rayn.mdx) (en anglais).

Ouvrez ensuite <https://ip.net.coffee/claude/>. Si l'IP de votre serveur s'affiche, vous êtes connecté.

## Avant de partir

- **Configurez et testez tout avant le départ.** Une fois sur un réseau restreint, télécharger le projet ou même ouvrir des outils d'IA peut devenir bien plus difficile.
- Installez les clients et importez les abonnements sur le téléphone et l'ordinateur, puis vérifiez que les deux nœuds se connectent.
- Si un réseau local n'atteint pas votre serveur, essayez d'abord un autre réseau (Wi-Fi de l'hôtel, données mobiles, autre opérateur). Si rien ne marche, l'IP du serveur est probablement bloquée sur place. Aucun réglage n'y changera rien : demandez une nouvelle IP à votre fournisseur.
- Gardez la connexion pour vous et votre famille. Ne la partagez pas.

## Vérifier le serveur plus tard

Envoyez ceci à l'IA (remplacez `bwg` par votre nom) :

```text
Merci de vérifier mon serveur selon le plan « claude-network-guide » : ssh bwg

Plan : https://github.com/clm031102-source/claude-network-guide
Téléchargez le projet et lisez la partie « 以后的复核和维护 » (vérifications
et maintenance ultérieures) de modules/vps/skills/claude-network-guide/SKILL.md.
Commencez par vérifier seulement, dites-moi ce qui a échoué et pourquoi, et ne corrigez rien sans mon accord.
N'affichez ni mots de passe, ni URLs d'abonnement, ni clés dans la discussion. Parlez-moi en français.
```

La documentation détaillée ([dépannage](./skills/claude-network-guide/references/troubleshooting.md), [notes de conception](./skills/claude-network-guide/references/design.md)) n'existe pour l'instant qu'en chinois ; votre IA peut la lire pour vous.

## Retours et suggestions



## Confidentialité

- Ce projet ne contient aucune information sur un serveur réel.
- Les mots de passe, clés, URLs d'abonnement et clés API de chaque serveur sont générés à neuf pendant la configuration et stockés uniquement sur le serveur et sur votre ordinateur. L'IA ne les affiche pas dans la discussion.
- Ne publiez nulle part votre fichier de connexion, vos URLs d'abonnement ou vos clés, et n'en faites pas de capture.
- Pour signaler un problème de sécurité, voir [SECURITY.md](./SECURITY.md).

La possibilité de se connecter, et la vitesse, dépendent aussi du réseau local et de l'acheminement du serveur. Ce projet garantit que le serveur est correctement configuré, pas qu'une même IP soit joignable depuis tous les pays et tous les opérateurs.

## Licence

[MIT](./LICENSE)
