let currentRound = 1;
let totalRounds = 0;
let isGameActive = false; // Flag to prevent re-running start logic

// ===== Utils =====
function rankToName(rank) {
    if (rank === 1) return "ace";
    if (rank === 11) return "jack";
    if (rank === 12) return "queen";
    if (rank === 13) return "king";
    return rank.toString();
}

function shapeToName(shape) {
    return ["hearts", "diamonds", "clubs", "spades"][shape];
}

function cardImage(card) {
    const rank = rankToName(card.rank);
    const shape = shapeToName(card.shape);
    return `/static/cards/${rank}_of_${shape}.png`;
}

function addCard(containerId, card) {
    console.log(`[UI] Adding card to ${containerId}:`, card);
    const img = document.createElement("img");
    img.src = cardImage(card);
    img.className = "card";
    document.getElementById(containerId).appendChild(img);
}

function toggleGameplayButtons(disabled) {
    const hitBtn = document.querySelector("button[onclick='hit()']");
    const standBtn = document.querySelector("button[onclick='stand()']");

    if (hitBtn && !isGameActive) hitBtn.disabled = disabled;
    if (standBtn && !isGameActive) standBtn.disabled = disabled;
}

// ===== Game Flow (Command Senders) =====

async function startGame() {
    console.log("[Action] Start Game Button Clicked");
    const roundsInput = document.getElementById("rounds").value;
    totalRounds = parseInt(roundsInput);

    await fetch("/connect", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ rounds: totalRounds })
    });
    // The Watcher will handle the UI switch
}

async function hit() {
    console.log("[Action] Sending HIT command...");
    await fetch("/hit", { method: "POST" });
}

async function stand() {
    console.log("[Action] Sending STAND command...");
    await fetch("/stand", { method: "POST" });
}

// ===== Rendering Logic =====

function renderStartRound(cards) {
    console.log("[Render] Starting Round with cards:", cards);

    // Ensure UI is switched
    document.getElementById("setup").style.display = "none";
    document.getElementById("game").style.display = "block";
    isGameActive = true;

    // Reset Board
    document.getElementById("player-cards").innerHTML = "";
    document.getElementById("dealer-cards").innerHTML = "";
    document.getElementById("result").innerText = "";
    document.getElementById("round-info").innerText = `Round ${currentRound} / ${totalRounds}`;

    // Render 3 Initial Cards
    if(cards && cards.length >= 3) {
        addCard("player-cards", cards[0]);
        addCard("player-cards", cards[1]);
        addCard("dealer-cards", cards[2]);
    }
}

function renderHit(card) {
    console.log("[Render] Player Hit:", card);
    addCard("player-cards", card);
    if (card.result !== 0) endRound(card.result);
}



function renderStand(cards) {
    console.log("[Render] Player Stood. Dealer cards:", cards);
    cards.forEach(card => addCard("dealer-cards", card));

    if(cards.length > 0) {
        endRound(cards[cards.length - 1].result);
    }
}

function endRound(result) {
    const text = result === 3 ? "You won 🎉" : result === 2 ? "You lost ❌" : "Tie 🤝";
    document.getElementById("result").innerText = text;

    currentRound++;

    if (currentRound <= totalRounds) {
        console.log("[Game] Waiting for next round...");
    } else {
        // Wait 2 seconds so the user can see the final "You Won/Lost" message
        setTimeout(() => {
            // === GAME OVER LOGIC (Now inside the timeout) ===
            document.getElementById("round-info").innerText = "Game Over";
            isGameActive = false;

            // 1. Get Elements
            const overlay = document.getElementById("game-over-overlay");
            const video = document.getElementById("end-video");

            // 2. Show the Overlay (CSS handles the centering)
            overlay.style.display = "flex";

            // 3. Play the video automatically
            video.play().catch(e => console.log("Auto-play blocked by browser:", e));

        }, 2000);

    }
}

// =========================================================
// THE HIGH-SPEED WATCHER (100ms Interval)
// =========================================================
setInterval(async () => {
    try {
        const res = await fetch("/status");
        const data = await res.json();

        // 1. Check Connection (Lobby -> Game)
        // We check !isGameActive to ensure we don't reset the UI unnecessarily
        if (data.connected && !isGameActive && document.getElementById("setup").style.display !== "none") {
            console.log("[Watcher] Connection detected! Switching to Game View.");
            totalRounds = data.rounds;
            document.getElementById("rounds").value = totalRounds;
            document.getElementById("setup").style.display = "none";
            document.getElementById("game").style.display = "block";
            isGameActive = true;
        }

        // 2. Check for Updates (Start / Hit / Stand)
        // This handles inputs from BOTH Terminal and Web clicks
        if (data.update !== "none" ) {

           if (data.update === "start") {
                setTimeout(() => {
                    toggleGameplayButtons(false);
                    renderStartRound(data.data);
                }, 3000);

            }
            else if (data.update === "hit") {
                renderHit(data.data);

                // CHECK RESULT: If result is not 0 (0 = Continue), round is over
                if (data.data.result !== 0) {
                    toggleGameplayButtons(true); // Disable
                }
            }
            else if (data.update === "stand") {
                renderStand(data.data);

                // Stand always ends the round (Dealer plays out), so disable immediately
                toggleGameplayButtons(true);
            }

        }

        if (data.win_rate >= 0){
            console.log(data.win_rate)
            document.getElementById("win-rate").innerText = `${data.win_rate}%`
        }

    } catch (e) {
        // Silence errors if server is down (common during restart)
    }
}, 100); // <--- 100ms Interval (Very Fast)