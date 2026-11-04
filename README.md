# Untitled Tower Defense

Tower defense spēle ar kāršu uzlabojumiem. Pa līkumotu ceļu uz tavu māju nāk skudras: sākumā dažas, vēlāk miljoni. Novieto torņus, uzlabo tos un savāc kārtis, lai izdzīvotu pēc iespējas ilgāk. Kad spēle beidzas, rezultāts tiek nosūtīts serverim un parādās līderu tabulā mājaslapā.

## Uzstādīšana (vienreiz)

No projekta mapes:

**Windows (PowerShell)**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Linux / macOS**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Palaišana

Vienmēr no projekta mapes (tās, kur ir `game/`, `client/` un `api/`), ar aktivizētu `.venv`.

### Spēle

```bash
python -m client.main
```

Strādā arī `python client/main.py`.

Spēle pati palaiž rekordu serveri fonā, ja tas vēl nestrādā, un aizver to, kad aizver spēli. Tāpēc pietiek ar šo vienu komandu: rezultāti saglabāsies un parādīsies mājaslapā.

### Tikai serveris un mājaslapa

```bash
uvicorn api.main:app --reload
```

- Līderu tabula: <http://localhost:8000/> (pāradresē uz `/pages/index.html`)
- Noteikumi, vadība un torņu statistika: <http://localhost:8000/pages/rules.html>
- API pārbaude ar pogām: <http://localhost:8000/docs>

Lapas var atvērt arī ar dubultklikšķi no mapes `api/templates/`. Ja serveris strādā, tās tāpat ielādē īstos rezultātus; ja nestrādā, rāda 5 izdomātus spēlētājus un saglabātos torņu skaitļus.

Ja serveris jau strādā atsevišķā terminālī, spēle izmanto to pašu un otru nepalaiž.

## Kā spēlēt

1. Izvēlnē ieraksti savu vārdu un nospied **Enter** (vai *Start Game*).
2. Ar taustiņiem **1–4** vai klikšķi uz ikonas apakšā izvēlies torni un uzklikšķini uz zāles, lai to novietotu.
3. Nospied **Atstarpi**, lai sāktu pirmo vilni. Tālāk viļņi sākas paši.
4. Uzklikšķini uz torņa un nospied **E**, lai to uzlabotu.
5. Ik pēc 5 raundiem izvēlies 1 no 3 kārtīm un uzliec to kāršu izvēlnē (**TAB**).
6. Kad bāzes dzīvības nokrīt līdz 0, rezultāts tiek saglabāts. **R** sāk jaunu spēli.

### Vadība

| Taustiņš | Ko dara |
|---|---|
| `Enter` | Izvēlnē sāk spēli |
| `Atstarpe` | Sāk nākamo vilni uzreiz |
| `1` `2` `3` `4` | Tornis, ferma, saldētājs, bumba |
| Kreisais klikšķis | Novieto torni / izvēlas torni |
| `Shift` + vilkšana | Novieto daudz parasto torņu pēc kārtas un uzlabo tos, ja pietiek naudas (ne apvienotos) |
| Labais klikšķis, `Q` | Atceļ novietošanu / izvēli |
| `E` | Uzlabo izvēlēto torni |
| `C` | Pārdod izvēlēto torni (50% no cenas) |
| `TAB` | Kāršu izvēlne (arī poga *CARDS*) |
| `F` | Torņu apvienošana (arī poga *FUSE*) |
| `P` | Pauze / turpināt |
| `Esc` | Izvēlne: turpināt vai iziet |
| `R` | Beigu ekrānā: jauna spēle no nulles |
| `F11` | Pilnekrāna režīms |
| `F5` | Atkļūdošanas izvēlne: FPS, skudru skaits, pogas +1M/+1B/+1T naudas, +100 dzīvību un pāreja uz jebkuru raundu (uzklikšķini uz ROUND, ieraksti numuru, `Enter`) |

## Spēles iespējas

- **Bezgalīgi viļņi.** Katrs vilnis ir par 10% lielāks, un skudru vairogi aug par 10% katrā raundā.
- **4 torņi ar 5 līmeņiem.** Tornis šauj pa priekšējo skudru, ferma dod naudu, saldētājs palēnina skudras zonā, bumbas sprādziens trāpa visām skudrām rādiusā (4. līmenis izšauj 3 raķetes).
- **Kāršu sistēma.** 5 retumi (Common 90%, Rare 5%, Epic 4%, Legendary 0,99%, Secret 0,01%), līdz 5 uzliktām kārtīm vienlaikus.
- **Trade-up.** Jebkuras 3 viena retuma kārtis (piemēram, 3 dažādas Common) → 1 nejauša augstāka retuma kārts, jebkuras 20 Legendary → Secret kārts.
- **Totem of Undying.** Atdzīvina bāzi un 20 sekundes dedzina visas skudras.
- **Torņu apvienošana.** Ar pogu *FUSE* (vai `F`) vairākus 5. līmeņa torņus var apvienot vienā daudz spēcīgākā 80×80 tornī:
  - **Plasma Railgun:** 10 torņi + 1 saldētāji + 1 bumbas + 50 000 000 naudas. Ļoti ātri plazmas šāvieni, mazs sprādziens katrā trāpījumā, palēnina.
  - **Missile Silo:** 10 bumbas + 4 torņi + 1 saldētāji + 100 000 000 naudas (katrs nākamais Silo maksā 2× vairāk). 3 lielas raķetes zalvē, ātra pārlāde, palēnina.
  - **Cryo Spire:** 10 saldētāji + 2 torņi + 1 bumbas + 40 000 000 naudas. Spēcīga palēnināšana (summējas ar saldētājiem) un sala sprādziens visām skudrām zonā.
- **Vārdu filtrs.** Spēle un serveris neļauj vārdus ar rupjībām, arī maskētus (ar cipariem, atstarpēm, atkārtotiem burtiem vai līdzīgi skanošus). Saraksts ir `game/blocked_names.txt`.
- **100 miljardi skudru.** Vienādas skudras tiek apvienotas „paciņās”, tāpēc spēle rit ar 60 FPS arī ar milzīgiem viļņiem.

Visi torņu skaitļi ir noteikumu lapā un tiek nolasīti tieši no `game/game.py`.

## API

| Metode un adrese | Ko dara | Atbilde |
|---|---|---|
| `GET /hello` | Pārbauda, vai serveris strādā | 200 |
| `POST /scores` | Saglabā rezultātu `{"player": "Anna", "score": 900, "round": 12}` | 201 |
| `GET /scores/top?limit=10` | Labākie rezultāti, lielākie punkti pirmie (limit 1–100, noklusējumā 10) | 200 |
| `GET /players/{name}/stats` | Spēļu skaits, labākais rezultāts un augstākais raunds | 200, vai 404, ja tāda spēlētāja nav |
| `GET /game-info` | Torņu un kāršu dati noteikumu lapai | 200 |
| `POST /admin/login` | Pārbauda administratora paroli | 200, vai 401, ja parole nav pareiza |
| `DELETE /scores/{id}` | Izdzēš rezultātu (vajag paroli) | 204, 401 vai 404 |
| `PATCH /scores/{id}` | Nomaina vārdu rezultātam `{"player": "Anna"}` (vajag paroli) | 200, 401, 404 vai 422 |

Parole tiek sūtīta galvenē `X-Admin-Password`, un serveris to salīdzina ar privāto failu `admin_password.txt` projekta mapē. Šis fails ir `.gitignore`, tāpēc tas nenonāk GitHub un paliek tikai tavā datorā. Ja faila nav vai tas ir tukšs, administratora iespējas ir izslēgtas.

Sliktie dati tiek noraidīti ar **422** un netiek ierakstīti: tukšs vārds, vārds garāks par 20 simboliem, rupjš vārds, negatīvi punkti vai negatīvs raunds.

Rezultāti glabājas SQLite datubāzē `game.db` projekta mapē, tāpēc tie paliek arī pēc servera restarta. Visi SQL vaicājumi izmanto `?` vietas (aizsardzība pret SQL injekciju). `game.db` nenonāk GitHub (`.gitignore`).

## Projekta struktūra

Katra koda faila sākumā ir satura rādītājs ar birkām, piemēram `[G4]` failā `game/game.py`. Meklē birku ar `Ctrl+F`, lai nokļūtu tieši pie tās sadaļas.

```
game/          spēles noteikumi (bez pygame): skudras, torņi, kārtis, punkti
client/        attēlošana un ievade (pygame)
  main.py      viss klients: izvēlne, spēle, pauze, beigu ekrāns, kārtis, serveris
  textures/    attēli un fonts
api/           serveris (FastAPI)
  main.py      API adreses
  db.py        SQLite datubāze
  templates/   mājaslapa: index.html (rekordi), rules.html (kā spēlēt)
  static/      style.css, app.js, fonts
requirements.txt
```

## Ja kaut kas nestrādā

| Ko redzi | Ko darīt |
|---|---|
| `No module named 'game'` / `'api'` | Palaid no projekta mapes: `python -m client.main` vai `uvicorn api.main:app --reload` |
| `No module named 'pygame'` / `'fastapi'` | Aktivizē `.venv` un palaid `pip install -r requirements.txt` |
| `address already in use` | Serveris jau strādā citā terminālī: aptur to ar `Ctrl+C` vai lieto to pašu |
| Beigu ekrānā „SERVER OFFLINE” | Serveris nepaspēja palaisties: palaid to ar `uvicorn api.main:app` un spēlē vēlreiz |
| Mājaslapā „Serveris nav palaists” | Palaid spēli vai serveri, tad atjauno lapu |
