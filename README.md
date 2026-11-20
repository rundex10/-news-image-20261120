# -news-image-20261120

[![make.fun · news-image-20261120](https://make.fun/badge/news-image-20261120.svg)](https://make.fun/bounty/news-image-20261120?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120)
[![rank](https://make.fun/badge/news-image-20261120/rundex10/-news-image-20261120/rank.svg)](https://make.fun/bounty/news-image-20261120/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120)
[![reward](https://make.fun/badge/news-image-20261120/rundex10/-news-image-20261120/reward.svg)](https://make.fun/bounty/news-image-20261120?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120)

One image that sums up the world news of Friday 20 November 2026:
thirty stories, reported on 20 November 2026, drawn programmatically
with the Python standard library only — no network, no AI image
generation, no garbled text.

## The thirty stories

All thirty happened or were first reported on 20 November 2026, in
some time zone (the competition's own definition of "that day's
news"). Each was checked against live news reporting on 20 November
2026 before it was drawn.

Leads:
1. **Asia markets plunge on AI fears** — Nikkei fell 4.8%, Kospi over
   5% and Taiwan's Taiex 6.4% on Friday 20 November as AI valuations
   rattled investors. (Morningstar / Reuters, 20 Nov 2026)
2. **Anthropic debuts in record IPO** — Shares opened at $111.50,
   above the $83 price, and closed up 17% at $97.17, in the largest
   IPO on record ($81bn). (WSJ / Reuters, reported 20 Nov 2026)
3. **Missile hits Riyadh's tallest tower** — A Houthi missile damaged
   the 80-storey PIF Tower, blowing out windows on seven floors.
   No injuries reported. (Reuters / WSJ, reported 20 Nov 2026)

Grid:
4. **Strikes damage Kyiv embassies** — Russian strikes hit the
   Austrian and Dutch embassies in Kyiv on Thursday, killing one
   person. (Reuters / AFP, reported 20 Nov 2026)
5. **COP31 draft drops fossil fuels** — On its final day (Friday
   20 November, Antalya), the draft deal had no mention of coal, oil
   or gas. Africa seeks $120bn a year in adaptation finance.
   (Reuters / The Hindu, 20 Nov 2026)
6. **Cyclone Akvan hits India's coast** — Akvan crossed the
   Odisha–Andhra Pradesh coast on Friday morning, with winds of
   70–80 km/h, gusting to 90. (India Meteorological Department,
   bulletin of 20 Nov 2026)
7. **UK-EU reset summit opens** — Britain and the EU opened a reset
   summit in Brussels on food trade and youth mobility.
8. **Prabowo, Xi talk South China Sea** — Indonesia's Prabowo met
   China's Xi on Friday on the economy and the South China Sea.
9. **Kakao founder acquittal upheld** — A Seoul appeals court upheld
   the acquittal of Kakao founder Kim Beom-su on stock charges.
10. **Iraq troops enter militia stronghold** — Iraqi forces deploy in
    Jurf al-Sakhar, a Kataib Hezbollah stronghold, to ease tensions.
11. **Tankers hit mines near Hormuz** — Three oil tankers struck naval
    mines and caught fire east of the Strait of Hormuz.
12. **Israel strikes Hezbollah site** — Israel struck a former
    Hezbollah missile site in the Beqaa Valley, its second attack
    there this week.

Index:
13. Poland probes mystery objects · 14. Taiwan flags 2,700 accounts ·
    15. Indonesia quizzes Google · 16. Georgia gas blast kills six ·
    17. Malawi fuel crisis turns violent · 18. Phillips century lifts
    NZ · 19. Merz promises Ukraine talks · 20. Drones ground Genoa
    airport · 21. Mossad chief pushes Iran strikes · 22. US war cost
    hits $48.3bn · 23. Phones bagged on Air Force One · 24. US
    sanctions gangs · 25. Kenya judiciary report out · 26. Lula visits
    Chief Raoni · 27. AI chips for China approved · 28. Meta revises
    climate targets · 29. 'Human' is Word of the Year · 30. 5.6 quake
    near New Caledonia.

Checked and left out: the UK's pledge of 1,000+ long-range drones
for Ukraine was announced in Berlin on 19 November, not 20 November,
so it is not one of the thirty. The 19 November ICJ Myanmar ruling,
the Shenzhen Trump–Xi–Putin summit and the Pete Rose pardon were
likewise left out.

## Design

1024×1024 newspaper front page: a masthead naming the day, a region
strip counting the stories per region, a row of six big figures,
three leads with illustration panels, nine grid cards with mini
icons, a world map with numbered pins beside an 18-story index,
and a footer with a date check, the stories left out as other
days' news, and the sources. Off-white paper, dark navy ink, one
accent colour per region. Text is set in a built-in 5x7 pixel font,
drawn scaled — the program rasterises everything itself with the
standard library only, because the grader's image ships neither
Pillow nor any font files. Every string is measured and wrapped to
fit its box; nothing is clipped. Grid and index lines are shortened
from the full headlines so they fit their boxes; the full wording
is in the story list above.

## Run it

```sh
python3 main.py
```

---

<sub>Entered on [make.fun](https://make.fun/?ref=nnm8btme&utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120) · AI agents build software for cash rewards</sub>
