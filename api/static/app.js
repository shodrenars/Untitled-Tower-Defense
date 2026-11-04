// ----------------------------------------------------------------------------
// [J1] SETTINGS AND TEXT
// ----------------------------------------------------------------------------
// Server address. Pages opened by double click must use the full address,
// pages opened from the server can use a short relative one.
//   =====================================================================
//   api/static/app.js - WHAT MAKES THE WEBSITE LIVE
//   =====================================================================
//   Used by both pages. It fetches data from the server and fills the
//   tables. If the server is off, the examples in the HTML stay on screen.
//
//   TABLE OF CONTENTS - search for a tag (Ctrl+F "[J3]") to jump to it
//     [J1]   Settings and text
//     [J2]   Tower table setup
//     [J3]   Small helpers
//     [J4]   Leaderboard
//     [J5]   Player lookup
//     [J6]   Secret admin mode
//     [J7]   Rules page: tower tables
//     [J8]   Rules page: fused towers and cards
//     [J9]   Page start

const API = location.protocol === "file:" ? "http://127.0.0.1:8000" : "";

// Text shown for each answer the server gives to an admin action.
const ADMIN_MESSAGES = {
    200: "Vārds nomainīts.",
    204: "Rezultāts izdzēsts.",
    401: "Nepareiza parole.",
    404: "Tāda rezultāta vairs nav.",
    422: "Šāds vārds nav atļauts.",
};

// adminPassword stays null until you log in. It is only kept in memory,
// so reloading the page logs you out. shownScores is the current table.
let adminPassword = null;
let shownScores = [];

// Card rarity names as shown on the page.
const RARITY_NAMES = {
    common: "Common",
    rare: "Rare",
    epic: "Epic",
    legendary: "Legendary",
    secret: "Secret",
};

// ----------------------------------------------------------------------------
// [J2] TOWER TABLE SETUP
// ----------------------------------------------------------------------------
// One entry per tower. columns lists each table column as a title and a
// function that picks the value out of that level's stats.
const TOWERS = [
    {
        key: "turret",
        name: "Tornis",
        hotkey: "1",
        desc: "Šauj pa vienu skudru: vienmēr pa to, kas tikusi vistālāk pa ceļu. Pirmais šāviens noņem vairogu, tad dzīvības.",
        columns: [
            ["Cost", (s) => num(s.cost)],
            ["Damage", (s) => num(s.damage)],
            ["Cooldown", (s) => s.cooldown + " s"],
            ["Range", (s) => s.range + " px"],
            ["DPS", (s) => num(Math.round(s.damage / s.cooldown))],
        ],
    },
    {
        key: "farm",
        name: "Ferma",
        hotkey: "2",
        desc: "Nešauj. Katra raunda sākumā dod naudu, un augstākos līmeņos palielina naudu par katru bojājuma punktu. Kartē var būt ne vairāk kā 5 fermas.",
        columns: [
            ["Cost", (s) => num(s.cost)],
            ["Money per round", (s) => num(s.money_given)],
            ["Money multiplier", (s) => "×" + s.money_multi],
        ],
    },
    {
        key: "freeze",
        name: "Saldētājs",
        hotkey: "3",
        desc: "Palēnina visas skudras savā zonā. Parastais skudru ātrums ir 60 px/s. Ja skudra ir vairāku saldētāju zonā, darbojas spēcīgākais.",
        columns: [
            ["Cost", (s) => num(s.cost)],
            ["Range", (s) => s.range + " px"],
            ["Ant speed in zone", (s) => s.freeze_multi + " px/s"],
        ],
    },
    {
        key: "bomb",
        name: "Bumba",
        hotkey: "4",
        desc: "Mērķē uz priekšējo skudru, un sprādziens trāpa VISĀM skudrām sprādziena rādiusā. 4. līmenis izšauj 3 raķetes pēc kārtas uz dažādām vietām.",
        columns: [
            ["Cost", (s) => num(s.cost)],
            ["Damage", (s) => num(s.damage)],
            ["Cooldown", (s) => s.cooldown + " s"],
            ["Range", (s) => s.range + " px"],
            ["Explosion radius", (s) => s.explosion_radius + " px"],
            ["Rockets", (s) => s.rockets],
        ],
    },
];

// ----------------------------------------------------------------------------
// [J3] SMALL HELPERS
// ----------------------------------------------------------------------------
// Formats numbers with Latvian spacing, or short form for huge numbers.
function num(n) {
    if (n >= 1e12) {
        return Number(n).toExponential(2);
    }
    return Number(n).toLocaleString("lv-LV");
}

// Makes text safe for the page, so a player name cannot inject HTML.
function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

// Fetches JSON from the server, and throws an error with the status code
// if the answer is not OK.
async function getJson(path) {
    const res = await fetch(API + path);
    if (!res.ok) {
        const error = new Error("HTTP " + res.status);
        error.status = res.status;
        throw error;
    }
    return res.json();
}

// Updates the green or red server status line.
function setStatus(online, text) {
    const box = document.getElementById("server-status");
    if (!box) {
        return;
    }
    box.classList.toggle("online", online);
    box.classList.toggle("offline", !online);
    box.querySelector(".label").textContent = text;
}

// Shows the database's UTC time in local Latvian format.
function formatDate(value) {
    if (!value) {
        return "";
    }
    const date = new Date(value.replace(" ", "T") + "Z");
    if (isNaN(date)) {
        return value;
    }
    return date.toLocaleString("lv-LV", { dateStyle: "short", timeStyle: "short" });
}

// ----------------------------------------------------------------------------
// [J4] LEADERBOARD
// ----------------------------------------------------------------------------
// Fetches the scores and rebuilds the table. It runs every 10 seconds.
async function loadScores() {
    const body = document.querySelector("#scores tbody");
    const note = document.getElementById("scores-note");
    try {
        const scores = await getJson("/scores/top?limit=100");
        setStatus(true, "Serveris strādā · rezultāti atjaunojas ik pēc 10 sekundēm");

        // No real scores yet: keep the example rows. In admin mode the table
        // empties instead, so a deleted row does not stay on screen.
        if (scores.length === 0) {
            note.textContent = "Vēl nav neviena īsta rezultāta. Šie ir izdomāti spēlētāji: nospēlē spēli, un tavs rezultāts parādīsies šeit.";
            if (adminPassword !== null) {
                body.innerHTML = "";
            }
            return;
        }

        // Remember the scores so admin buttons can find the one clicked.
        shownScores = scores;
        body.innerHTML = scores
            .map((s, i) => {
                const cls = i === 0 ? ' class="first"' : "";
                const tools = adminPassword === null ? "" : `<td class="tools"><button data-action="rename" data-id="${s.id}">Mainīt</button> <button data-action="delete" data-id="${s.id}">Dzēst</button></td>`;
                return `<tr${cls}><td class="num">${i + 1}</td><td>${escapeHtml(s.player)}</td><td class="num">${num(s.score)}</td><td class="num">${s.round}</td><td>${formatDate(s.created_at)}</td>${tools}</tr>`;
            })
            .join("");
        note.textContent = "Rādīti top " + scores.length + " rezultāti (ne vairāk kā 100).";
    } catch (error) {
        setStatus(false, "Serveris nav palaists · rādīti piemēri");
    }
}

// ----------------------------------------------------------------------------
// [J5] PLAYER LOOKUP
// ----------------------------------------------------------------------------
// The "Spēlētāja statistika" search form.
function setupLookup() {
    const form = document.getElementById("lookup");
    const result = document.getElementById("lookup-result");
    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const name = document.getElementById("lookup-name").value.trim();
        if (!name) {
            return;
        }
        result.textContent = "Meklēju…";
        try {
            const stats = await getJson("/players/" + encodeURIComponent(name) + "/stats");
            result.innerHTML = `<strong>${escapeHtml(stats.player)}</strong>: nospēlētas ${stats.games} spēles · labākais rezultāts <strong>${num(stats.best_score)}</strong> · augstākais raunds ${stats.best_round}`;
        } catch (error) {
            if (error.status === 404) {
                result.textContent = "Spēlētājs „" + name + "” vēl nav nospēlējis nevienu spēli.";
            } else {
                result.textContent = "Serveris nav palaists, tāpēc statistiku nevar nolasīt.";
            }
        }
    });
}

// ----------------------------------------------------------------------------
// [J6] SECRET ADMIN MODE
// ----------------------------------------------------------------------------
// Sends a request with the password in a header. The server checks the
// password, because anything in this file can be read by anyone.
async function adminRequest(password, method, path, data) {
    const res = await fetch(API + path, {
        method,
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: data ? JSON.stringify(data) : undefined,
    });
    return res.status;
}

// Handles one Mainīt or Dzēst click, then reloads the table.
async function changeScore(action, score) {
    let status;
    if (action === "delete") {
        if (!confirm(`Dzēst ${score.player} rezultātu ${num(score.score)}?`)) {
            return;
        }
        status = await adminRequest(adminPassword, "DELETE", "/scores/" + score.id);
    } else {
        // Empty or cancelled means do nothing.
        const player = prompt("Jaunais vārds", score.player);
        if (!player) {
            return;
        }
        status = await adminRequest(adminPassword, "PATCH", "/scores/" + score.id, { player });
    }
    document.getElementById("admin-note").textContent = ADMIN_MESSAGES[status] || "Kļūda " + status;
    await loadScores();
}

// Tests a password. A failed connection counts as a failed login.
async function adminLogin(password) {
    try {
        return await adminRequest(password, "POST", "/admin/login");
    } catch (error) {
        return 0;
    }
}

// Connects the invisible button, the password box and the row buttons.
function setupAdmin() {
    const dialog = document.getElementById("admin-dialog");
    const input = document.getElementById("admin-password");
    const note = document.getElementById("admin-note");
    const openDialog = () => {
        if (adminPassword === null) {
            dialog.showModal();
        }
    };

    // The invisible button in the nav opens the password box.
    document.getElementById("secret").addEventListener("click", openDialog);

    // The rules page sends you here with #admin to open the box at once.
    if (location.hash === "#admin") {
        history.replaceState(null, "", location.pathname);
        openDialog();
    }

    // Password submitted: on success add the Admin column and the buttons.
    document.getElementById("admin-login").addEventListener("submit", async (event) => {
        event.preventDefault();
        const password = input.value;
        input.value = "";
        if (await adminLogin(password) !== 200) {
            document.getElementById("admin-result").textContent = ADMIN_MESSAGES[401];
            return;
        }
        adminPassword = password;
        dialog.close();
        document.querySelector("#scores thead tr").insertAdjacentHTML("beforeend", "<th>Admin</th>");
        note.textContent = "Admin režīms: vari mainīt vārdus un dzēst rezultātus.";
        await loadScores();
    });

    // One click handler for all row buttons, since rows get rebuilt often.
    document.querySelector("#scores tbody").addEventListener("click", async (event) => {
        const button = event.target.closest("button");
        if (!button) {
            return;
        }
        const score = shownScores.find((s) => s.id === Number(button.dataset.id));
        try {
            await changeScore(button.dataset.action, score);
        } catch (error) {
            note.textContent = "Serveris nav palaists.";
        }
    });
}

// ----------------------------------------------------------------------------
// [J7] RULES PAGE: TOWER TABLES
// ----------------------------------------------------------------------------
// Builds one tower's table with a row for each level.
function towerTable(tower, stats) {
    const head = "<tr><th class=\"num\">Level</th>" + tower.columns.map(([title]) => `<th class="num">${title}</th>`).join("") + "</tr>";
    const rows = Object.keys(stats)
        .sort((a, b) => a - b)
        .map((level) => "<tr><td class=\"num\">" + level + "</td>" + tower.columns.map(([, value]) => `<td class="num">${value(stats[level])}</td>`).join("") + "</tr>")
        .join("");
    return `<div class="table-scroll"><table><thead>${head}</thead><tbody>${rows}</tbody></table></div>`;
}

// Replaces the saved tower tables with live numbers from the game.
function renderTowers(info) {
    const box = document.getElementById("towers");
    box.innerHTML = TOWERS.map(
        (tower) => `<section class="tower panel">
            <h3>${tower.name} · taustiņš <kbd>${tower.hotkey}</kbd></h3>
            <p class="desc">${tower.desc}</p>
            ${towerTable(tower, info.towers[tower.key])}
        </section>`
    ).join("");
}

// ----------------------------------------------------------------------------
// [J8] RULES PAGE: FUSED TOWERS AND CARDS
// ----------------------------------------------------------------------------
// Words for the fusion recipes, and each fused tower's description.
const PART_NAMES = { turret: "torņi", freeze: "saldētāji", bomb: "bumbas" };
const FUSED_DESC = {
    railgun: "Ļoti ātri, smagi plazmas šāvieni pa priekšējo skudru, katrs trāpījums ar mazu sprādzienu, un skudras zonā tiek nedaudz palēninātas.",
    silo: "Izšauj 3 lielas raķetes pēc kārtas uz dažādām vietām, ātri pārlādējas un nedaudz palēnina skudras zonā. Katrs nākamais Missile Silo maksā 2× vairāk.",
    spire: "Spēcīga palēnināšanas zona, kas summējas ar saldētājiem, un sala sprādziens, kas trāpa visām skudrām zonā.",
};

// Builds the fused tower panels with their recipes and level tables.
function renderFused(info) {
    const box = document.getElementById("fused");
    if (!box || !info.fused) {
        return;
    }
    box.innerHTML = Object.entries(info.fused)
        .map(([kind, f]) => {
            const recipe = Object.entries(f.recipe).map(([part, n]) => `${n} ${PART_NAMES[part]}`).join(" + ") + ` + ${num(f.stats[1].cost)} naudas`;
            const head = '<tr><th class="num">Level</th><th class="num">Cost</th><th class="num">Damage</th><th class="num">Cooldown</th><th class="num">Range</th><th class="num">Slows to</th></tr>';
            const rows = Object.keys(f.stats)
                .sort((a, b) => a - b)
                .map((lv) => {
                    const s = f.stats[lv];
                    return `<tr><td class="num">${lv}</td><td class="num">${num(s.cost)}</td><td class="num">${num(s.damage)}</td><td class="num">${s.cooldown} s</td><td class="num">${s.range} px</td><td class="num">${Math.round(s.slow * 100)}%</td></tr>`;
                })
                .join("");
            return `<section class="tower panel"><h3>${escapeHtml(f.name)}</h3><p class="desc">${FUSED_DESC[kind] || ""}</p><p class="desc"><strong>Recepte (visi ${info.fusion_level}. līmenī):</strong> ${recipe}</p><div class="table-scroll"><table><thead>${head}</thead><tbody>${rows}</tbody></table></div></section>`;
        })
        .join("");
}

// Builds the rarity table and the full card list.
function renderCards(info) {
    const rarities = document.querySelector("#rarities tbody");
    rarities.innerHTML = info.rarities
        .map((r) => {
            const color = `rgb(${r.color.join(",")})`;
            const trade = r.trade_up ? `any ${r.trade_up} ${RARITY_NAMES[r.name]} → 1 random ${RARITY_NAMES[info.rarities[info.rarities.indexOf(r) + 1].name]}` : "can't be traded up";
            return `<tr><td><span class="rarity" style="background:${color}"></span>${RARITY_NAMES[r.name]}</td><td class="num">${r.chance}%</td><td>${trade}</td></tr>`;
        })
        .join("");
    const list = document.getElementById("card-list");
    list.innerHTML = info.cards
        .map((c) => `<div class="card ${c.rarity}"><div class="tier">${RARITY_NAMES[c.rarity].toUpperCase()}</div>${escapeHtml(c.name)}</div>`)
        .join("");
}

// Fetches the game's data and fills the rules page.
async function loadGameInfo() {
    try {
        const info = await getJson("/game-info");
        renderTowers(info);
        renderFused(info);
        renderCards(info);
        setStatus(true, "Serveris strādā · skaitļi nolasīti tieši no spēles koda");
    } catch (error) {
        setStatus(false, "Serveris nav palaists · rādīti saglabātie skaitļi");
    }
}

// ----------------------------------------------------------------------------
// [J9] PAGE START
// ----------------------------------------------------------------------------
// Leaderboard page: load scores, refresh them, set up the forms.
if (document.getElementById("scores")) {
    loadScores();
    setInterval(loadScores, 10000);
    setupLookup();
    setupAdmin();
}

// Rules page: load the data. The invisible button goes to the leaderboard
// because that is where the scores are.
if (document.getElementById("towers")) {
    loadGameInfo();
    document.getElementById("secret").addEventListener("click", () => {
        location.href = "index.html#admin";
    });
}
