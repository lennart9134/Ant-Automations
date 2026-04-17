// Popup UI logic. Reads/writes the pause flag in chrome.storage.local.
// Enterprise policy can forbid pausing via managed_schema.pauseAllowed.

const PAUSE_KEY = "ant.paused";

async function render() {
  const [{ [PAUSE_KEY]: paused }, managed] = await Promise.all([
    chrome.storage.local.get(PAUSE_KEY),
    chrome.storage.managed.get("pauseAllowed"),
  ]);
  const pill = document.getElementById("status-pill");
  const btn = document.getElementById("toggle-pause");
  const isPaused = Boolean(paused);
  pill.textContent = isPaused ? "paused" : "active";
  pill.className = `pill ${isPaused ? "paused" : "active"}`;
  btn.textContent = isPaused ? "Resume" : "Pause";
  const pauseAllowed = managed.pauseAllowed !== false;
  btn.disabled = !pauseAllowed;
  if (!pauseAllowed) {
    btn.title = "Your organisation has disabled manual pause.";
  }
}

document.getElementById("toggle-pause").addEventListener("click", async () => {
  const { [PAUSE_KEY]: paused } = await chrome.storage.local.get(PAUSE_KEY);
  await chrome.storage.local.set({ [PAUSE_KEY]: !paused });
  render();
});

render();
