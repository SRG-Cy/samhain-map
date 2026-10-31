---
title: "Halloween started in Ireland. I put Kerry's 1890s ghost stories back on the map, and code wouldn't let the AI invent a single place"
published: false
tags: devchallenge, hf26challenge, gemma, opensource
---

*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 4: Ghost in the Machine](https://dev.to/challenges/hacktoberfest-week4-2026-10-26)*

Halloween started here. Long before plastic pumpkins, Samhain was the night at the end of October when the Irish said the wall between this world and the other one wore thin, and the dead walked the roads.

I live in Ireland, and a few weeks ago I found out that in the 1890s an American folklorist, Jeremiah Curtin, sat by firesides in Kerry and wrote down what people told him: a man walking to Sneem at night who meets a ghost and fights it off with a steel sword, a midwife carried away to a fairy fort on a horse that turns out to be a plough beam, a drowned girl walking a strand in her bare feet asking for shoes. He printed thirty of them in 1895 as *Tales of the Fairies and of the Ghost World*.

Every one of those tales happens somewhere real. The road to Sneem. Blackwater bridge. Ventry strand. You can still walk most of them. But in the book they're just words on a page, and the old spellings (Lochlein, Rahonain) don't match any modern map.

So I built **Samhain Map**: click a place in Kerry and read the ghost stories that happened there.

## What I Built

![Samhain Map: the Kerry coast with glowing marks where the tales happen, filters for ghosts, fairies and the dead returning, and a list of tales](https://raw.githubusercontent.com/SRG-Cy/samhain-map/main/docs/img/home.jpg)

{{TALE VIEW SCREENSHOT OR GIF}}

- **A map of Munster** with a glowing mark at every place the tales name. Click one and you get the tales set there.
- **Each tale** has a one-line summary, the line that shows its ghost or fairy, every place it names with a ✓ or ✗ and the reason, the full text, and a link to the scanned 1895 page.
- **Filters** by what haunts the tale: ghosts, fairies, the dead returning, a seal woman, a banshee, saints.
- **A count of what the checker refused**, right on the front page. That number matters to me as much as the pins.

The rule behind all of it: **Gemma reads. Code decides.**

## Demo

**Live:** [samhain-map.onrender.com](https://samhain-map.onrender.com) (no sign-up, works on a phone)

Try: filter by **Ghost**, click **Sneem**, open *The Ghost of Sneem*, then scroll to "Places in this tale".

## Code

{% github SRG-Cy/samhain-map %}

## How I Built It

```plaintext
1895 scan (archive.org) ─▶ code splits it into 30 tales
each tale ─▶ Gemma 4 26B (JSON mode): beings, summary, every place + the exact words it came from
          ─▶ code: is the quote really in the tale? is the name in the quote?
          ─▶ code: is it a real place? (16,947 Munster townlands from Tailte Éireann + 10,859 GeoNames places)
          ─▶ old spelling not found? Gemma suggests a modern one; code accepts it only if it exists near the tale's other places
          ─▶ map
```

### Gemma only points at the text

For every place, Gemma has to return the place **and the exact words it came from**. Code then checks two things: the quote is really in the tale, and the name is really in the quote. If either fails, the place is refused, and the map says so.

Across all 30 tales, Gemma reported 95 place names. Two failed the quote check, and they surprised me: **neither was invented.** Both places are really in the tales. Gemma just changed one word while copying:

| Tale says | Gemma quoted |
|---|---|
| "…the fort **on** the place where I am living now, in Lismore." | "**in** the place where I am living now, in Lismore." |
| "…the eldest son to marry **and** Gort na Leachtan (the field of the stone heaps)…" | "**is** Gort na Leachtan (the field of the stone heaps) as fortune." |

I kept the rule strict anyway. A checker that lets "close enough" through is a checker that will one day let a made-up townland through. Losing two pins is the cheaper mistake.

### A real place, or nothing

A name that passes the quote check still isn't pinned until it matches a real place: one of 16,947 Munster townlands from Tailte Éireann's boundary data, or a town, hill, lake or bridge from GeoNames, inside Munster. "Munster" or "Kerry" are listed but never pinned: too broad to be a place you could stand.

Many names exist more than once. Ireland has several Ballymores. When a name matches more than one real place, code picks the one nearest the tale's other places, and the tale card says it made that choice.

### The 1890s spellings

Curtin wrote names as he heard them. *Lochlein* is Lough Leane. *Rahonain* is probably Rahinnane. Modern maps have never heard of the first spelling.

So there's a second, small Gemma pass: for every name the map couldn't find, Gemma suggests up to three modern spellings. **Code still decides.** A suggestion is accepted only if that place exists *and* lies within 30 km of the tale's other places. Those pins are labelled "via modern spelling, suggested by Gemma", so you can see which ones the model helped with.

| Curtin wrote | Gemma suggested | Code said |
|---|---|---|
| Lochlein | Lough Leane | ✓ pinned: the big lake at Killarney (two tales) |
| Skneem | Sneem | ✓ pinned |
| Awnascawil | Annascaul | ✓ pinned: a real village in the right corner of Kerry |
| Castlemain | Castlemaine | ✓ pinned (two tales) |
| Kilshanig | Kilshannig | ✓ pinned |
| Rahin | Rahan | ✗ refused: Rahan exists, but 124 km from the tale's other places |
| Dun Lean | Dunlea | not pinned: no such place |
| Drumfada | Drumfada | not pinned: no such place on modern maps |

The Rahan one is my favourite row in the project. Gemma's suggestion was a real place. It just wasn't *this* place, and only the distance check could tell.

This pass was also the flakiest part of the build. Asked about 29 names at once, Gemma reasoned past every time limit I gave it. Even 5 at a time timed out. One name per call, with a hard 150-second limit, got answers for 15 of 26 names after two runs; the rest (Rahonain among them) simply stay unpinned. In the end 8 place names are on the map because of this pass, and every one of them is labelled as a suggestion.

### Measuring it

For 7 of the shorter tales, every real place in Ireland they name was labelled by hand: 22 places. Then I compared two versions of the map: one that pins everything Gemma reported, and the real one.

| Tale | Places in the tale | Gemma found | Gemma alone would also pin | Pinned (correct / wrong) |
|---|---|---|---|---|
| The Midwife of Listowel | 1 | 1 | | 1 / 0 |
| Tom Connors and the Dead Girl | 5 | 5 | | 3 / 0 |
| James Murray and Saint Martin | 3 | 3 | "Kerry" | 3 / 0 |
| The Ghost of Sneem | 7 | 7 | | 6 / 0 |
| The Dead Mother | 3 | 3 | "America" | 2 / 0 |
| Tim Sheehy Sent Back… | 1 | 1 | | 1 / 0 |
| The Four-leafed Shamrock | 2 | 2 | | 2 / 0 |
| **Total** | **22** | **22** | **2** | **18 / 0** |

- **Gemma's reading was excellent.** It found all 22 places and invented none.
- **Every pin on the map in these tales is right.** The 4 it couldn't pin are 1890s spellings that no modern map has: Rahin, Rahonain, Drumfada and "Ventry Strand".
- **The honest limits:** it's 7 tales and 22 places, not a benchmark. {{LABEL_NOTE}}

### Things that went wrong

- **Gemma 4 31B returned server errors all afternoon** on AI Studio, so everything ran on Gemma 4 26B (the mixture-of-experts one). Because the weights are open, switching was one line.
- **At temperature 0, Gemma 26B got stuck in its own reasoning:** "Wait, 'Sneem' is a setting. Wait, 'Blackwater bridge' is a setting." for 26,000 characters. JSON mode fixed it: about 11 seconds a tale.
- **Cork city wasn't on the map.** City centres have no townlands, so the city sits in a hole in the county outline. Points just outside the outline now count.
- **The free tier rate-limited me** halfway through. Every reply is cached per tale, so the run picked up where it stopped.
- **A Drummond in Tipperary dragged Waterville to Limerick.** In *Murderous Ghosts*, the only "Drummond" in Munster is 178 km away in Tipperary. My first checker trusted a single match as a reference point, and then picked the Waterville in Limerick because it was "nearest". Now only places in Kerry and Cork count as reference points, and a lone match that far from the rest of the tale is refused with the distance.
- **Then my fix was too strict.** Tales where someone travels to Cork city lost Dingle and Brandon Mountain, because Cork pulled the centre of the tale east. A trip to the city isn't where a tale is set, so cities no longer count as reference points.

## Why Does Open Innovation Matter?

**Archives don't want their collections fed to AI companies, and I understand why.** Ireland's largest folklore archive, duchas.ie, blocks AI crawlers by name in its robots.txt. Those are people's grandparents' stories.

That's exactly why the model being open matters. Gemma's weights are public, so an archive can run this same pipeline on its own server, on its own collection, and nothing ever leaves the building. I ran it on a hosted Gemma for the demo, using a public-domain book. The National Folklore Collection could run it in-house without asking anyone's permission.

**It's checkable.** Same open model, same prompt, same public-domain book, same public maps: anyone can re-run it and argue with any pin. Every Gemma reply is committed in `data/extract/`.

**It isn't locked inside a service that might disappear.** When the bigger Gemma was down, I changed one line. If the hosted API went away tomorrow, the same weights run on a laptop.

**Where a closed model might do better:** probably the old spellings. A bigger model might know more 1890s Kerry place names. It would still need the same checker, because a confident model inventing a townland is the one thing a map of real places can't have.

## The Spirit of It

{{the moment: a place you know, or showing someone their own townland's tale}}

## Prize Categories

- **Best Use of Gemma:** Gemma 4 26B reads all 30 tales, picks out the beings, the summary and every place with its exact quote, and suggests modern spellings for 1890s names. Every answer is checked in code before it reaches the map.
- **Best Use of Render:** the whole map is a static site deployed from a `render.yaml` Blueprint in the repo. Every push to `main` redeploys it, so each re-run of the checker goes live on its own.

---

*Tales: Jeremiah Curtin (1895), public domain, scan by Cornell University Library via archive.org. Townland boundaries © Tailte Éireann, CC BY 4.0. Places: GeoNames, CC BY 4.0. Built with Claude Code; I directed it and checked the results.*
