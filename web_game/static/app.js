let currentRound = 1;
let totalRounds = 0;

// ===== Utils =====
function rankToName(rank) {
    if (rank === 1) return "ace";
    if (rank === 11) return "jack";
    if (rank === 12) return "queen";
    if (rank === 13) return "king";
    return rank.toString();
}

function shapeToName(shape) {
    return ["clubs", "diamonds", "hearts", "spades"][shape];
}

function cardImage(card) {
    const rank = rankToName(card.rank);
    const shape = shapeToName(card.shape);
    return `/static/cards/${rank}_of_${shape}.png`;
}

function addCard(containerId, card) {
    const img = document.createElement("img");
    img.src = cardImage(card);
    img.className = "card";
    document.getElementById(containerId).appendChild(img);
}

// ===== Game Flow =====
async function startGame() {
    totalRounds = parseInt(document.getElementById("rounds").value);

    await fetch("/connect", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ rounds: totalRounds })
    });

    document.getElementById("setup").style.display = "none";
    document.getElementById("game").style.display = "block";

    startRound();
}

async function startRound() {
    document.getElementById("player-cards").innerHTML = "";
    document.getElementById("dealer-cards").innerHTML = "";
    document.getElementById("result").innerText = "";

    document.getElementById("round-info").innerText =
        `Round ${currentRound} / ${totalRounds}`;

    const res = await fetch("/start", { method: "POST" });
    const cards = await res.json();

    addCard("player-cards", cards[0]);
    addCard("player-cards", cards[1]);
    addCard("dealer-cards", cards[2]);
}

async function hit() {
    const res = await fetch("/hit", { method: "POST" });
    const card = await res.json();

    addCard("player-cards", card);

    if (card.result !== 0) {
        endRound(card.result);
    }
}

async function stand() {
    const res = await fetch("/stand", { method: "POST" });
    const cards = await res.json();

    cards.forEach(card => {
        addCard("dealer-cards", card);
    });

    const last = cards[cards.length - 1];
    endRound(last.result);
}

function endRound(result) {
    const text =
        result === 3 ? "You won 🎉" :
        result === 2 ? "You lost ❌" :
        "Tie 🤝";

    document.getElementById("result").innerText = text;

    currentRound++;
    if (currentRound <= totalRounds) {
        setTimeout(startRound, 2000);
    } else {
        document.getElementById("round-info").innerText = "Game Over";
    }
}
