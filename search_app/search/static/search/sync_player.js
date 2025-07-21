let socketURL;
const opts = { path: "/socket.io", transports: ["websocket"] };

if (location.hostname === "localhost" || location.hostname === "127.0.0.1") {
  socketURL = "http://127.0.0.1:5001";
} else {
  socketURL = "wss://ivitestproject.ru";
}

export const socket = io(socketURL, opts);
export let isSyncing = false;

socket.on("connect", () => console.log("✅ Socket connected", socket.id));
socket.on("connect_error", (err) => console.error("❌ connect_error", err));

const params = new URLSearchParams(location.search);
export let room    = params.get("room");
export let animeId = params.get("anime_id");
export let episode = params.get("episode");

export const syncedPlayers = new Set();
if (room && animeId && episode) syncedPlayers.add(`${animeId}_${episode}`);

if (room) {
  socket.emit("join", room);
  console.log("Подключен к комнате:", room);
}

export function attachSyncHandlerToPlayer(player, anime_id, episode) {
  if (!room || !player) return;
  setupSyncForPlayer(player, anime_id, episode, room);
}

function setupSyncForPlayer(player, anime_id, episode, roomName) {
  if (!roomName) return;

  const key = `${anime_id}_${episode}`;
  const players = document.querySelectorAll(
    `video[data-anime-id="${anime_id}"][data-episode="${episode}"]`
  );
  player = players[players.length - 1];

  function sendSync(data) {
    socket.emit("sync", { room: roomName, anime_id, episode, ...data });
  }

  player.addEventListener("play", () => {
    if (!isSyncing) sendSync({ action: "play", time: player.currentTime });
  });
  player.addEventListener("pause", () => {
    if (!isSyncing) sendSync({ action: "pause", time: player.currentTime });
  });
  player.addEventListener("seeked", () => {
    if (!isSyncing) sendSync({ action: "seek", time: player.currentTime });
  });

  console.log("▶️  Sync enabled for", key);
}

function detachSyncHandlerFromPlayer(player) {
  const clone = player.cloneNode(true);
  player.parentNode.replaceChild(clone, player);
}

socket.on("sync", (data) => {
  const { anime_id, episode, action, time } = data;
  const player = document.querySelector(
    `video[data-anime-id="${anime_id}"][data-episode="${episode}"]`
  );
  if (!player) return;

  isSyncing = true;

  switch (action) {
    case "play":
      player.currentTime = time;
      player.play().catch((e) => console.error("Видео play error", e));
      break;
    case "pause":
      player.currentTime = time;
      player.pause();
      break;
    case "seek":
      player.currentTime = time;
      break;
  }
