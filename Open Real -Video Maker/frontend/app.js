const API_BASE = window.OPENREEL_API_BASE || "";

let STYLES = [];
let SELECTED_STYLE = "anime";
let CURRENT_JOB = null;
let POLL_TIMER = null;

const el = (id) => document.getElementById(id);

async function loadStyles() {
  try {
    const res = await fetch(`${API_BASE}/api/styles`);
    const data = await res.json();
    STYLES = data.styles;
  } catch (e) {
    STYLES = [
      { id: "anime", name: "Anime Story", emoji: "🌸" },
      { id: "horror", name: "Suspense Horror", emoji: "🕯️" },
      { id: "comedy", name: "Absurd Comedy", emoji: "🤪" },
      { id: "scifi", name: "Sci-Fi Adventure", emoji: "🚀" },
      { id: "nature", name: "Nature & Pets", emoji: "🐾" },
      { id: "history", name: "Ancient History", emoji: "🏛️" },
    ];
  }
  renderStylePicker();
}

function renderStylePicker() {
  const wrap = el("stylePicker");
  wrap.innerHTML = "";
  STYLES.forEach((s) => {
    const chip = document.createElement("div");
    chip.className = "style-chip" + (s.id === SELECTED_STYLE ? " active" : "");
    chip.innerText = `${s.emoji} ${s.name}`;
    chip.onclick = () => {
      SELECTED_STYLE = s.id;
      renderStylePicker();
    };
    wrap.appendChild(chip);
  });
}

async function loadGallery() {
  try {
    const res = await fetch(`${API_BASE}/api/videos`);
    const data = await res.json();
    renderGallery(data.videos || []);
  } catch (e) {
    renderGallery([]);
  }
}

function fmtDuration(sec) {
  sec = Math.round(sec || 0);
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function renderGallery(videos) {
  const grid = el("gallery");
  const empty = el("emptyState");
  grid.innerHTML = "";
  if (!videos.length) {
    empty.classList.remove("hidden");
    return;
  }
  empty.classList.add("hidden");
  videos.forEach((v) => {
    const card = document.createElement("div");
    card.className = "video-card";
    card.innerHTML = `
      <div class="thumb-wrap">
        <img src="${API_BASE}${v.thumb_url}" loading="lazy" />
        <div class="play-badge"><span>▶</span></div>
        <div class="duration-badge">${fmtDuration(v.duration)}</div>
      </div>
      <div class="card-meta">
        <div class="card-prompt">${escapeHtml(v.prompt)}</div>
        <div class="card-style">${v.style_name || v.style}</div>
      </div>
    `;
    card.onclick = () => openPlayer(v);
    grid.appendChild(card);
  });
}

function escapeHtml(str) {
  const d = document.createElement("div");
  d.innerText = str || "";
  return d.innerHTML;
}

function openPlayer(v) {
  const modal = el("playerModal");
  const video = el("modalVideo");
  video.src = `${API_BASE}${v.video_url}`;
  el("modalPrompt").innerText = v.prompt;
  el("downloadBtn").href = `${API_BASE}${v.video_url}`;
  el("downloadBtn").setAttribute("download", `${v.id}.mp4`);
  el("deleteBtn").onclick = async () => {
    if (!confirm("Delete this video?")) return;
    await fetch(`${API_BASE}/api/videos/${v.id}`, { method: "DELETE" });
    closePlayer();
    loadGallery();
  };
  modal.classList.remove("hidden");
}

function closePlayer() {
  const modal = el("playerModal");
  const video = el("modalVideo");
  video.pause();
  video.src = "";
  modal.classList.add("hidden");
}

async function startGeneration() {
  const prompt = el("prompt").value.trim();
  if (!prompt) {
    el("prompt").focus();
    return;
  }
  const btn = el("generateBtn");
  btn.disabled = true;
  el("btnLabel").innerText = "⏳ Queuing…";
  el("progressCard").classList.remove("hidden");
  el("progressBar").style.width = "0%";
  el("progressPct").innerText = "0%";
  el("progressStage").innerText = "Queued";

  try {
    const res = await fetch(`${API_BASE}/api/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, style: SELECTED_STYLE }),
    });
    const data = await res.json();
    if (!data.job_id) throw new Error(data.error || "Failed to start job");
    CURRENT_JOB = data.job_id;
    el("btnLabel").innerText = "🎬 Generating…";
    pollJob(data.job_id);
  } catch (e) {
    alert("Could not start generation: " + e.message);
    resetGenerateButton();
  }
}

function pollJob(jobId) {
  clearInterval(POLL_TIMER);
  POLL_TIMER = setInterval(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/jobs/${jobId}`);
      const job = await res.json();
      el("progressBar").style.width = `${job.progress || 0}%`;
      el("progressPct").innerText = `${job.progress || 0}%`;
      el("progressStage").innerText = job.stage || job.status;

      if (job.status === "done") {
        clearInterval(POLL_TIMER);
        resetGenerateButton();
        el("progressCard").classList.add("hidden");
        loadGallery();
        el("prompt").value = "";
        if (job.result) openPlayer(job.result);
      } else if (job.status === "error") {
        clearInterval(POLL_TIMER);
        resetGenerateButton();
        alert("Generation failed: " + (job.error || "unknown error"));
        el("progressCard").classList.add("hidden");
      }
    } catch (e) {
      // network hiccup, keep polling
    }
  }, 1200);
}

function resetGenerateButton() {
  el("generateBtn").disabled = false;
  el("btnLabel").innerText = "✨ Generate video";
}

el("generateBtn").addEventListener("click", startGeneration);
el("refreshBtn").addEventListener("click", loadGallery);
el("closeModal").addEventListener("click", closePlayer);
el("playerModal").querySelector(".modal-backdrop").addEventListener("click", closePlayer);
el("prompt").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) startGeneration();
});

loadStyles();
loadGallery();
