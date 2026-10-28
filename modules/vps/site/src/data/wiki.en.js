// English Wiki entries: same slugs and structure as wiki.js.
export const WIKI_EN = {
  ip: {
    title: "IP address", group: "Networking basics",
    one: "An IP address is a device's street address on the network. Data packets use it to know where to go and where they came from.",
    like: "Like the recipient and sender addresses on a parcel. When a website receives your request, the \"sender address\" it sees is your IP — enough to roughly tell your country and internet provider.",
    here: "Your server has a **public IP** (four groups of numbers, such as `203.0.113.10`). Once your app connects to it, websites see the server's IP instead of your home IP. The IP is also written into the server's certificate, so visiting `https://IP` does not show a security warning.",
    myths: [
      "\"An IP pinpoints my front door\": usually it only reveals country, city and provider.",
      "\"A NAT machine has a public IP too, so it works\": NAT machines share one IP and each gets only a few ports, so the ports this setup needs (80, 443…) are not available.",
      "\"IPv4 and IPv6 are the same thing\": they are two separate address systems. The nodes use IPv4; see \"System proxy vs TUN\" for the IPv6 setting in the app.",
    ],
  },
  dns: {
    title: "Domain names and DNS", group: "Networking basics",
    one: "DNS translates easy-to-remember site names (domains) into IP addresses.",
    like: "Like your phone's contact list: you remember \"Alex\", but the phone dials a number. DNS is that contact list, and your computer looks it up before opening any site.",
    here: "The subscription comes with DNS already set up: Chinese sites are looked up with Alibaba's and Tencent's encrypted DNS (DoH); foreign sites that are not on any list are not looked up locally at all — they are handed to your server. That is fast and does not leak which foreign sites you visit.",
    myths: [
      "\"Changing DNS gets me around the firewall\": DNS only looks up addresses; it does not carry your data.",
      "\"DNS is encrypted\": classic DNS is plain text and visible along the way; only DoH (DNS over HTTPS) is encrypted.",
    ],
  },
  "dns-leak": {
    title: "DNS leak", group: "Networking basics",
    one: "When you visit a site, its name gets looked up by your local network's DNS, so others can tell where you are and what you visit. That is a DNS leak.",
    like: "You take a private car somewhere, but before leaving you ask the guard downstairs how to get there. The ride is private, yet the guard already knows your destination.",
    here: "A common cause is IP-based rules such as `GEOIP,CN`: to decide whether a site's IP is Chinese, the app first looks it up with a Chinese DNS. In this setup every IP rule carries `no-resolve`, so unlisted foreign sites are never looked up locally — leak tests only see overseas DNS on the server's side.",
    myths: [
      "\"Any Chinese DNS in the test means a leak\": using Chinese DNS for Chinese sites is normal; what matters is whether foreign sites are looked up with Chinese DNS.",
      "\"A DNS leak exposes my exact IP\": it usually exposes your province and provider.",
    ],
  },
  proxy: {
    title: "Proxy, VPN, node, \"airport\"", group: "Networking basics",
    one: "A proxy is a middleman that visits websites for you; a node is your tunnel to the proxy server; an \"airport\" (机场) is a shared proxy service used by many people; a VPN is a related technology that joins your whole device to another network.",
    like: "A proxy is like a personal shopper: you say what to buy, they buy it and the shop only sees them. An airport is a team of shoppers serving many customers; your own server is a personal shopper serving only your family.",
    here: "The server you rent is the proxy server. It has two **nodes**: `name-Reality` (main, port 443) and `name-TLS` (backup, port 2443). The \"auto switch\" group in the app moves to the backup if the main one fails.",
    myths: [
      "\"More nodes is better\": nodes are for switching. For personal use, two (main + backup) are enough.",
      "\"A proxy slows down every site\": with routing rules, Chinese sites skip the proxy and stay fast.",
    ],
  },
  port: {
    title: "Ports", group: "Networking basics",
    one: "Ports number the different services on one server, so one IP can run many services at once.",
    like: "The IP is a building's address; the port is the room number. A delivery needs both.",
    here: "Ports used by this setup: `22` SSH, `80` certificate validation, `443` main node, `2443` backup node, `2096` subscription, `8318` CLIProxyAPI, `53998` 3x-ui panel. The firewall only allows these; everything else is closed.",
    myths: [
      "\"Opening more ports is more convenient\": every open port is another door to scan and attack. Close what you do not use.",
      "\"Moving SSH off port 22 makes it secure\": it stops some automated scans, but real security comes from key-only login.",
    ],
  },
  "tcp-udp": {
    title: "TCP and UDP", group: "Networking basics",
    one: "TCP and UDP are two ways to send data: TCP is reliable and ordered; UDP is fast but does not guarantee delivery.",
    like: "TCP is registered mail — signed for and resent if lost. UDP is a postcard — sent and forgotten, but quick.",
    here: "Web pages and AI chats mostly use TCP; video calls, games and the browser's WebRTC use UDP. Both nodes forward UDP. But Clash Verge's \"System Proxy\" mode only takes over TCP, so to stop WebRTC leaks you need \"Tun Mode\".",
    myths: ["\"UDP is insecure\": UDP is just a transport; security depends on what runs over it."],
  },
  webrtc: {
    title: "WebRTC", group: "Networking basics",
    one: "WebRTC is the browser's built-in real-time audio/video feature behind web video meetings and voice calls. It reports your IP to the outside over UDP.",
    like: "Like slipping a reply card with your home address into a parcel: the parcel went through a shopper, but the reply card comes straight back to your door.",
    here: "If Clash Verge only has \"System Proxy\" on, the browser's WebRTC bypasses the proxy and shows websites your real IP. The right fix is turning on \"Tun Mode\" so UDP also goes through the server — WebRTC keeps working. **Do not** use extensions that disable WebRTC instead; that breaks video and voice on web pages.",
    myths: [
      "\"No IP detected means it is fixed\": that usually means WebRTC has been disabled, not fixed.",
      "\"Some Chinese test sites still show a Chinese IP, so it is not fixed\": if that site uses a Chinese STUN server, Rule mode connects to it directly — that is expected.",
    ],
  },
  https: {
    title: "HTTPS and certificates", group: "Security",
    one: "HTTPS is encrypted web access; a certificate is an electronic document proving a site is who it claims to be.",
    like: "A certificate is an ID card issued by a recognised authority. Only with a proper ID does the browser show the padlock.",
    here: "The server uses a free, browser-trusted **IP certificate** from Let's Encrypt (it names the IP rather than a domain), so you do not need to buy a domain. These certificates last only about 6 days; the server checks every 6 hours and renews automatically. The subscription, panel and AI API all use it.",
    myths: [
      "\"A self-signed certificate is just as good\": browsers and many apps reject self-signed certificates; this setup never uses them.",
      "\"A padlock means the site is good\": it only means the connection is encrypted and the identity is genuine — not that the content is trustworthy.",
    ],
  },
  ssh: {
    title: "SSH, public and private keys", group: "Security",
    one: "SSH is how you log in to a server remotely and run commands on it. Logging in with keys is far safer than with a password.",
    like: "Keys are a lock and its only key: the **public key** is the lock, fitted to the server's door; the **private key** is the key, kept only on your computer. The door opens only when they match — nobody can guess it.",
    here: "Step 3 creates a key pair on your computer, puts the public key on the server and adds a name to `~/.ssh/config`. After that `ssh your-name` logs you straight in. Once set up, the server turns off password login and only accepts your computer's private key.",
    myths: [
      "\"I can send my private key to someone to take a look\": the private key is the server's key. Never give it to anyone.",
      "\"After changing computers I'm locked out\": use your provider's rescue console to log in and add the new computer's public key.",
    ],
  },
  firewall: {
    title: "Firewall", group: "Security",
    one: "A firewall decides which ports may accept connections from outside and rejects everything else.",
    like: "A building's doorman: registered visitors (open ports) get in; strangers stay outside.",
    here: "The server uses Ubuntu's built-in UFW firewall and only allows the ports this setup needs (see \"Ports\"). If you install another service, remember to allow its port too.",
    myths: ["\"A firewall makes me completely safe\": it only guards the door; the services behind open ports must be secure too (for example, key-only login)."],
  },
  vps: {
    title: "VPS and data-center routes", group: "Server",
    one: "A VPS is a virtual computer rented in a data center; the route is the network path from your home to that data center.",
    like: "Renting a VPS is like renting a small flat in another city; the route is the highway there — some are wide, some narrow, some jammed at night.",
    here: "A Los Angeles data center is recommended: relatively close to China and supported by AI services. 1 vCPU and 1 GB RAM are enough; choose Ubuntu 24.04 and KVM. The route affects speed from China and stability at peak hours; providers advertise routes such as CN2 GIA or 9929 — pricier routes are usually steadier at night.",
    myths: [
      "\"More server bandwidth means faster\": from China the bottleneck is usually the cross-ocean route, not the server.",
      "\"Cheap and expensive plans are the same\": similar in the daytime, very different at peak hours.",
    ],
  },
  "peak-hours": {
    title: "Why it is slower in the evening", group: "Server",
    one: "From 8 to 11 pm, routes from China abroad are most congested; packet loss rises and speed drops noticeably.",
    like: "Rush hour on the motorway: same road, more cars, more traffic jams.",
    here: "This is a route problem, not a configuration problem; the server's own bandwidth is usually far more than enough. BBR congestion control is on and helps somewhat. If peak hours matter a lot to you, choose a plan with a better route.",
    myths: ["\"Slow means I'm being throttled\": most of the time it is congestion — test again at another time."],
  },
  bbr: {
    title: "BBR", group: "Server",
    one: "BBR is a smarter way of controlling sending speed that runs steadier and faster on lossy routes.",
    like: "The old way slams the brakes at the first sign of traffic; BBR estimates how fast the road can go and drives smoothly.",
    here: "Step 3 turns BBR on automatically, together with some network tuning. Nothing for you to do.",
    myths: ["\"With BBR the route won't be congested\": it uses the route better but cannot change the route itself."],
  },
  "xray-reality": {
    title: "Xray, VLESS, Reality", group: "Parts of this setup",
    one: "Xray is the program on the server that actually forwards traffic; VLESS is the protocol it speaks with your app; Reality is a disguise that makes a node look like an ordinary HTTPS website.",
    like: "Xray is the driver, VLESS is the password between driver and passenger, Reality dresses the private car up as an ordinary taxi.",
    here: "The main node uses VLESS + Reality (port 443), disguised as the certificate site on your own IP — it does not borrow anyone else's site. The backup node uses VLESS + TLS (port 2443). The Xray version is pinned because newer versions stopped Shadowrocket from connecting.",
    myths: ["\"A disguise means it can never be blocked\": nothing is foolproof; if the IP is restricted somewhere, change the IP."],
  },
  "3x-ui": {
    title: "3x-ui", group: "Parts of this setup",
    one: "3x-ui is the web panel that manages Xray: nodes, users, traffic stats and subscriptions.",
    like: "The building management office: the driver (Xray) does the driving; the office handles schedules and accounts.",
    here: "Its address, username and password are in the login-info file on your desktop. You normally **don't need** to log in — nodes and subscriptions are already set up. Use it to check traffic or troubleshoot. Avoid editing nodes by hand; if something breaks, have AI repair it according to the setup.",
    myths: ["\"The panel needs regular maintenance\": once set up, it basically runs itself."],
  },
  subscription: {
    title: "Subscription", group: "Parts of this setup",
    one: "A subscription is a URL. Your app opens it to fetch the nodes and routing rules, and refreshes it periodically.",
    like: "A self-updating digital menu: when the kitchen changes a dish, you refresh and see it — no need to copy it out again.",
    here: "There are two subscription URLs: the **Clash subscription** for computers (Clash Verge) and routers (OpenClash), with full routing rules; and the **Shadowrocket subscription** for iPhone. Both are in the login-info file on your desktop. A subscription URL is the key to your line — never share it.",
    myths: [
      "\"The two URLs are interchangeable\": the formats differ; the Shadowrocket URL fails in Clash Verge.",
      "\"Import once and forget it\": apps refresh automatically; you can also tap \"Update\" after rules change.",
    ],
  },
  routing: {
    title: "Rule-based routing", group: "Parts of this setup",
    one: "Routing decides how each site is reached by rules: Chinese sites directly; foreign sites and AI tools through your server.",
    like: "A sorting clerk at the post office: local parcels go out directly, long-distance ones go on the private van.",
    here: "The subscription ships with over a hundred rules: AI tools (ChatGPT, Claude, Gemini…) have their own group; YouTube, Netflix, Telegram, Apple, Microsoft and Google each have theirs; Chinese domains and IPs go direct; everything else goes through the proxy. Rule files are hosted on your own server and refreshed daily, so apps never need GitHub. Choose \"Rule\" mode in the app.",
    myths: [
      "\"Global mode is more reliable\": Global sends Chinese sites abroad too — slower, and it can trigger risk controls on Chinese sites.",
      "\"I have to write rules myself\": they are already written; just import.",
    ],
  },
  tun: {
    title: "System proxy vs TUN", group: "Parts of this setup",
    one: "A system proxy only takes over web traffic from apps that respect system settings (mainly browsers); TUN mode takes over all traffic from every app, including UDP.",
    like: "A system proxy is a guide standing at the main door — only people who choose to follow get guided. TUN reroutes every exit of the building through the guide.",
    here: "This setup recommends turning on \"Tun Mode\" in Clash Verge: it stops the browser's WebRTC from exposing your real IP, and apps that ignore the system proxy still follow the rules. The first time, \"Install Service\" when prompted. Also set the \"IPv6\" switch in Clash Verge's settings by your network: on if the network has IPv6, or IPv6 traffic bypasses TUN; off if it doesn't, or WeChat may fail to send images.",
    myths: [
      "\"With TUN on, Chinese sites take a detour too\": no, routing rules still apply.",
      "\"Only one of System Proxy and TUN can be on\": both can be on without conflict; with TUN on, System Proxy can be either.",
    ],
  },
  "ip-reputation": {
    title: "IP reputation and risk control", group: "AI and accounts",
    one: "Websites score visitors' IPs: home broadband or data center, history of abuse, known proxy or not. Low scores can mean extra verification or restrictions.",
    like: "Like a bank checking a credit record: if lots of suspicious things happened on one IP, the next person on it gets a second look.",
    here: "Only you and your family use your server, so strangers cannot ruin its IP — an advantage over shared airports. It is still a data-center IP, so a few sites may ask for one more verification step. ip.net.coffee/claude/ shows Claude's score for the IP.",
    myths: [
      "\"Changing IP fixes account problems\": frequent IP changes or hopping between countries makes risk control more likely.",
      "\"A low score means it won't work\": usually it just means one more verification step.",
    ],
  },
  fingerprint: {
    title: "Time zone and browser fingerprint", group: "AI and accounts",
    one: "Besides the IP, websites also look at your time zone, language, OS, screen, fonts and more — together a \"browser fingerprint\".",
    like: "The IP is the address you give; the fingerprint is your accent and clothes. If you say you are in the US but sound and live like somewhere else, people ask more questions.",
    here: "If you use the same server long-term, you can set your computer's time zone to the server's location (for example Los Angeles) and avoid hopping between nodes in different countries. Turn off location permissions you do not need.",
    myths: ["\"A fingerprint can be completely disguised\": unnecessary and impossible. Consistency matters most."],
  },
  api: {
    title: "API and API keys", group: "AI and accounts",
    one: "An API is an interface programs use to call each other; an API key is the credential shown with each call — whoever has it can use it.",
    like: "An API is a bank counter; the API key is your access card. Lose the card and someone else can do business in your name.",
    here: "Your CLIProxyAPI has two \"cards\": the **API Key** that AI tools use to call the API, and the **management center login key** you use to log in to the admin page. Both are in the login-info file — never post them, screenshot them or upload them to GitHub.",
    myths: ["\"Keys in code are fine because the repo is private\": private repos get made public by mistake; keep keys in environment variables or a local config file."],
  },
  cliproxyapi: {
    title: "CLIProxyAPI", group: "Parts of this setup",
    one: "CLIProxyAPI is an open-source program on your server that turns your own AI accounts (such as ChatGPT or Claude) into a standard API for all kinds of AI tools.",
    like: "An adapter: you have several appliances with different plugs (AI tools); the adapter connects them all to one socket (your AI account).",
    here: "Its address is `https://your-IP:8318`. It starts empty; add your own accounts in the management center before using it. It checks for new versions every 30 minutes and only swaps versions at an idle moment, so it never interrupts a response in progress.",
    myths: [
      "\"Once installed, AI is free\": it only relays your own account; quota and costs are still your account's.",
      "\"Many people can share it\": sharing burns through quota quickly and may break the AI services' terms of use.",
    ],
  },
  "traffic-bandwidth": {
    title: "Traffic and bandwidth", group: "Server",
    one: "Traffic is how much data you can transfer per month (for example 1 TB); bandwidth is how fast it can flow at any moment (for example 1 Gbps).",
    like: "Traffic is the total on the water meter; bandwidth is the width of the pipe.",
    here: "For yourself and family, a few hundred GB to 1 TB per month is usually enough; lots of HD video uses more. Apps show this month's usage against 1 TB by default, with the reset day worked out from the provisioning date; tell AI if your plan differs.",
    myths: ["\"One speed test doesn't matter\": speed tests are data-hungry — one run can use several to tens of GB."],
  },
};

export const WIKI_GROUPS_EN = { "网络基础": "Networking basics", "安全": "Security", "服务器": "Server", "这套方案的部件": "Parts of this setup", "AI 和账号": "AI and accounts" };
