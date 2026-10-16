"""Generate animated terminal SVGs for the GitHub profile README."""
import html, os, pyfiglet

OUT = os.path.join(os.path.dirname(__file__), "assets")
os.makedirs(OUT, exist_ok=True)

W = 880
PAD = 22
BAR = 34
FS = 14
CW = 8.45          # approx monospace char width at 14px
LH = 21
FONT = "'JetBrains Mono','Fira Code','SF Mono',Menlo,Consolas,'DejaVu Sans Mono','Liberation Mono',monospace"

# black / red / white theme (keys kept as role names from the original palette)
C = dict(bg="#000000", bar="#0b0b0b", border="#262626", fg="#f2f2f2", dim="#7a7a7a",
         green="#ff2a2a", cyan="#ff6b6b", amber="#ff2a2a", red="#ff6b6b", blue="#f2f2f2")

HOST = "zepphen@roadrunner"
PROMPT = [(HOST, "green"), (":", "fg"), ("~", "blue"), ("$ ", "fg")]
PLEN = len(HOST) + 4

TYPE = 0.045   # seconds per typed char
OUTSTEP = 0.07 # seconds between printed lines


def esc(s):
    return html.escape(s, quote=False)


class Term:
    def __init__(self, title, start=0.5):
        self.title = title
        self.t = start
        self.lines = []  # (segments, kind, begin, dur, nchars, prefix_chars, lh)

    def out(self, *segs, gap=None, lh=LH):
        segs = [(s, "fg") if isinstance(s, str) else s for s in segs]
        self.lines.append((segs, "out", self.t, 0, 0, 0, lh))
        self.t += OUTSTEP if gap is None else gap
        return self

    def blank(self):
        return self.out("", gap=0.03)

    def typed(self, prefix, text, color="fg", pause=0.35):
        """prefix (list of segs) shows instantly, text is typed char by char."""
        plen = sum(len(s) for s, _ in prefix)
        segs = list(prefix) + [(text, color)]
        dur = max(len(text), 1) * TYPE
        self.lines.append((segs, "type", self.t, dur, len(text), plen, LH))
        self.t += dur + pause
        return self

    def cmd(self, text, pause=0.35):
        return self.typed(PROMPT, text, "fg", pause)

    def render(self, name, cursor=True):
        n = len(self.lines) + (1 if cursor else 0)
        body_h = sum(l[6] for l in self.lines) + (LH if cursor else 0)
        H = BAR + PAD + body_h + PAD - 6
        o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
             f'font-family="{FONT}" font-size="{FS}">']
        o.append(f'<title>{esc(self.title)}</title>')
        # window chrome
        o.append(f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="10" fill="{C["bg"]}" stroke="{C["border"]}"/>')
        o.append(f'<path d="M0.5 {BAR} V10.5 a10 10 0 0 1 10 -10 H{W-10.5} a10 10 0 0 1 10 10 V{BAR} Z" fill="{C["bar"]}"/>')
        o.append(f'<line x1="0.5" y1="{BAR}" x2="{W-0.5}" y2="{BAR}" stroke="{C["border"]}"/>')
        for i, col in enumerate(["#ff2a2a", "#3a3a3a", "#3a3a3a"]):
            o.append(f'<circle cx="{20+i*20}" cy="{BAR/2}" r="6" fill="{col}" opacity="0.85"/>')
        o.append(f'<text x="{W/2}" y="{BAR/2+5}" text-anchor="middle" fill="{C["dim"]}" font-size="13">{esc(self.title)}</text>')

        y = BAR + PAD + 4
        defs = []
        for i, (segs, kind, begin, dur, nch, plen, lh) in enumerate(self.lines):
            cid = f"c{i}"
            top = y - lh + 6
            if kind == "out":
                anim = f'<set attributeName="width" to="{W}" begin="{begin:.2f}s" fill="freeze"/>'
            else:
                w0 = plen * CW
                vals = [0] + [w0 + k * CW for k in range(nch + 1)] + [W]
                n_ = len(vals)
                # first value (hidden) until begin; then step through chars
                kt = [0] + [ (k + 1) / (n_) for k in range(n_ - 1)]
                kt[-1] = 1
                anim = (f'<animate attributeName="width" begin="{begin:.2f}s" dur="{dur+0.001:.3f}s" fill="freeze" '
                        f'calcMode="discrete" values="{";".join(f"{v:.1f}" for v in vals[1:])}"/>')
            defs.append(f'<clipPath id="{cid}"><rect x="0" y="{top}" width="0" height="{lh}">{anim}</rect></clipPath>')
            spans = "".join(f'<tspan fill="{C[c]}">{esc(s)}</tspan>' for s, c in segs)
            o.append(f'<text x="{PAD}" y="{y}" xml:space="preserve" clip-path="url(#{cid})">{spans}</text>')
            y += lh

        if cursor:
            # final idle prompt + blinking block cursor
            cid = "cfin"
            begin = self.t + 0.1
            defs.append(f'<clipPath id="{cid}"><rect x="0" y="{y-LH+6}" width="0" height="{LH}">'
                        f'<set attributeName="width" to="{W}" begin="{begin:.2f}s" fill="freeze"/></rect></clipPath>')
            spans = "".join(f'<tspan fill="{C[c]}">{esc(s)}</tspan>' for s, c in PROMPT)
            o.append(f'<text x="{PAD}" y="{y}" xml:space="preserve" clip-path="url(#{cid})">{spans}</text>')
            o.append(f'<rect x="{PAD + PLEN*CW:.1f}" y="{y-14}" width="{CW:.1f}" height="17" fill="{C["green"]}" opacity="0">'
                     f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.5;1" dur="1s" '
                     f'begin="{begin:.2f}s" repeatCount="indefinite"/></rect>')

        o.insert(2, "<defs>" + "".join(defs) + "</defs>")
        o.append("</svg>")
        path = os.path.join(OUT, name)
        with open(path, "w") as f:
            f.write("\n".join(o))
        return path


# ───────── 1. boot + login ─────────
t = Term("tty1 — roadrunner", start=0.3)
t.out(("[    0.000000] ", "dim"), "Linux version 6.6.6-utsa (aaban@roadrunner) #1 SMP", gap=0.12)
t.out(("[    0.004217] ", "dim"), "Command line: BOOT_IMAGE=/vmlinuz-curiosity root=/dev/brain", gap=0.12)
for svc in [[("Mounted /home/zephyr.", "fg")],
            [("Started Cyber Operations Service (NSA track).", "fg")],
            [("Started ", "fg"), ("never-give-up.service", "cyan"), (" (Restart=always).", "dim")],
            [("Started ", "fg"), ("learn-everything.service", "cyan"), (".", "fg")],
            [("Reached target Leadership.", "fg")],
            [("Reached target Multi-User System.", "fg")]]:
    t.out(("[  ", "fg"), ("OK", "green"), ("  ] ", "fg"), *svc, gap=0.22)
t.blank()
t.out("Roadrunner OS 2026 (tty1)", gap=0.4)
t.blank()
t.typed([("roadrunner login: ", "fg")], "zepphen", pause=0.3)
t.typed([("Password: ", "fg")], "••••••••••", color="dim", pause=0.5)
t.blank()
t.out(("Last login: from github.com — welcome back.", "dim"), gap=0.25)
t.blank()
for row in pyfiglet.figlet_format("AABAN", font="ansi_regular").rstrip("\n").split("\n"):
    t.out(("  " + row, "green"), gap=0.06, lh=16)
t.blank()
t.out(("  pronounced \"uh-bon\"", "dim"), ("  ·  ", "dim"), ("cs @ utsa", "cyan"), ("  ·  ", "dim"),
      ("nsa cyber operations track", "cyan"), gap=0.3)
t.out(("  a.k.a. ", "dim"), ("zepphen", "green"), ("  ·  ", "dim"), ("zephyr", "green"), gap=0.5)
t.blank()
t.cmd("cat motto.txt")
t.out(("  fix it ", "fg"), ("→", "green"), (" build it ", "fg"), ("→", "green"), (" break it ", "fg"),
      ("→", "green"), (" secure it ", "fg"), ("→", "green"), (" repeat.", "amber"))
t.render("01-boot.svg")

# ───────── 2. man page ─────────
t = Term("man aaban")
t.cmd("man aaban")
t.blank()
t.out(("AABAN(1)", "fg"), ("                          User Manuals                          ", "dim"), ("AABAN(1)", "fg"))
t.blank()
H = lambda s: (s, "amber")
t.out(H("NAME"))
t.out("    aaban — cyber operations student, hacker, engineer, leader, learner")
t.blank()
t.out(H("SYNOPSIS"))
t.out("    aaban [--hack] [--build] [--lead] [--learn] ", ("--everything", "green"))
t.blank()
t.out(H("DESCRIPTION"))
t.out("    Fixes things to learn how they're built.")
t.out("    Builds things to learn how they break.")
t.out("    Breaks things to learn how to secure them.")
t.blank()
t.out(H("STRENGTHS"))
t.out(("    --lead     ", "green"), "Leads teams and makes things happen.")
t.out(("    --learn    ", "green"), "Will learn anything, from anyone, anytime.")
t.blank()
t.out(H("BUGS"))
t.out("    Does not know how to give up. Tries to learn everything.")
t.out("    Reported upstream; marked ", ("WONTFIX", "red"), ". These are features.")
t.blank()
t.out(("SEE ALSO", "amber"))
t.out("    ", ("about.txt(1)", "blue"), ", ", ("neofetch(1)", "blue"), ", ", ("ps(1)", "blue"), ", ", ("events.log(5)", "blue"))
t.render("02-man.svg")

# ───────── 3. about ─────────
t = Term("~/about.txt")
t.cmd("cat about.txt")
t.out(("⌁ ", "green"), "cybersecurity · engineering · animals · cars · motorcycles")
t.out(("⌁ ", "green"), "jack of all trades: I love to do everything ", ("(a.k.a. \"the everything bagel\")", "cyan"))
t.out(("⌁ ", "green"), "I love being wrong about things so I can learn to do them right")
t.out(("⌁ ", "green"), "leadership roles? talk to me. I'll yap for hours about my projects,")
t.out("  and I'd love to hear about yours too")
t.render("03-about.svg")

# ───────── 3. neofetch (quick facts) ─────────
t = Term("~/neofetch")
t.cmd("neofetch")
logo = ["    _______    ", "   /       \\   ", "  |  >_     |  ", "  |         |  ", "   \\       /   ", "    \\_____/    ", "", ""]
info = [
    [(HOST, "green")],
    [("─" * len(HOST), "dim")],
    [("School", "amber"), ("  The University of Texas at San Antonio", "fg")],
    [("Major", "amber"), ("   B.S. Computer Science", "fg")],
    [("Track", "amber"), ("   NSA Cyber Operations", "fg")],
    [("Clubs", "amber"), ("   Cyber Jedis — Cyber Warfare Research Group", "fg")],
    [("", "fg"), ("        ACM @ UTSA — ClubHub & Rowdy Creators", "fg")],
    [("Org", "amber"), ("     D5 Interactive (d5i.store) — Co-Director", "fg")],
]
for lg, inf in zip(logo, info):
    t.out((f"{lg:<16}", "cyan"), *inf, gap=0.08)
t.render("04-neofetch.svg")

# ───────── 3b. experience (systemctl) ─────────
t = Term("~/experience")
t.cmd("systemctl status rmb-it.service")
t.out(("● ", "green"), ("rmb-it.service", "fg"), (" — IT Help Desk & Networking @ Right Medical Billing", "fg"))
t.out(("     Loaded: ", "dim"), "part-time / internship")
t.out(("     Active: ", "dim"), ("active (running)", "green"), ("  flexible schedule, pitching in as needed", "dim"))
t.out(("      Tasks: ", "dim"), "help desk support · troubleshooting · basic networking")
t.render("05-experience.svg")

# ───────── 4. projects (ps) ─────────
t = Term("~/projects")
t.cmd("ps aux --projects")
t.out(("  PID  STAT     COMMAND", "dim"))
procs = [("acm-clubhub", ""),
         ("rowdy-creators-drone", "  # ACM Rowdy Creators"),
         ("d5i-pentest-drone", "  # D5 Interactive"),
         ("ecommerce-bookstore", "  # class project, Barnes & Noble–inspired, not a real biz"),
         ("cure-research --ai-vulns", "  # CURE: AI vulnerability research")]
for i, (p, note) in enumerate(procs):
    t.out((f"  {101+i}  ", "fg"), ("running  ", "green"), (p, "fg"), (note, "dim"))
t.render("06-projects.svg")

# ───────── 5. learning (apt) ─────────
t = Term("~/learning")
t.cmd("sudo apt install kali-tools unix-cli osint nextjs drizzle-orm esp32 rpi")
t.out("Reading package lists... Done", gap=0.25)
pkgs = [("kali-linux (basic tools)", 6), ("linux/unix cli", 7), ("osint", 5), ("next.js", 5),
        ("drizzle-orm", 4), ("esp32", 6), ("raspberry-pi", 6)]
for name, n in pkgs:
    bar = "█" * n + "░" * (12 - n)
    t.out(("Setting up ", "fg"), (f"{name:<26}", "cyan"), (f"[{bar}] ", "green"), ("in progress", "amber"), gap=0.18)
t.render("07-learning.svg")

# ───────── 6. events ─────────
t = Term("~/events.log")
t.cmd("cat events.log")
t.out(("[  DONE  ] ", "green"), ("2022–2024   ", "dim"), "FIRST Robotics — 2023 FIRST in Texas State Champion")
t.out(" " * 23, "World Championship attendee")
t.out(("[  DONE  ] ", "green"), ("2023–2024   ", "dim"), "VEX Robotics — 2× World Championship attendee")
t.out(("[  DONE  ] ", "green"), ("2026-10     ", "dim"), "RowdyHacks XII — CTF participant")
t.out(("[UPCOMING] ", "amber"), ("2026-11-07  ", "dim"), "Rowdy Cyber Con — attending")
t.render("08-events.svg")

# ───────── 7. fun facts ─────────
t = Term("~/fun-facts")
t.cmd("fortune --all")
t.out(("⌁ ", "green"), "built my first robot when I was 4")
t.out(("⌁ ", "green"), "first-ever program: a Pokémon-inspired batch game")
t.out(("⌁ ", "green"), "tech inspirations: Marcus Hutchins, Joe Grand, Tristan Harris")
t.render("09-fun.svg")

# ───────── 8. favorites ─────────
def grid(items, cols, width, color="blue", prefix=None):
    for i in range(0, len(items), cols):
        segs = []
        for it in items[i:i+cols]:
            if prefix:
                segs.append((prefix, "cyan"))
                segs.append((f"{it:<{width-len(prefix)}}", "fg"))
            else:
                segs.append((f"{it:<{width}}", color))
        t.out(*segs)

t = Term("~/favorites")
t.cmd("ls ~/anime")
grid(["chainsaw-man/", "jujutsu-kaisen/"], 3, 26)
t.blank()
t.cmd("ls ~/games")
grid(["warframe/", "minecraft/", "marathon/",
      "fnaf-series/", "death-stranding-dc/", "death-stranding-2/"], 3, 26)
t.blank()
t.cmd("mpc playlist")
grid(["Billy Idol", "Snow Strippers", "beabadoobee", "Machine Girl", "Rory in early 20s",
      "Nirvana", "The Smashing Pumpkins", "Deftones", "Queens of the Stone Age", "Lexycat", "Muse"],
     3, 28, prefix="♫ ")
t.render("10-favorites.svg")

# ───────── 9. links header ─────────
t = Term("~/links")
t.cmd("ls ~/links")
t.out(("email  linkedin  twitter  instagram  discord  orcid  d5i.store", "blue"))
t.render("11-links.svg", cursor=False)

print("ok")
