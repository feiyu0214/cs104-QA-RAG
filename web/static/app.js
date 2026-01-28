/**
 * CS104 QA - Modern Web Interface
 * Vanilla JavaScript with clean architecture
 */

// ========================================
// Configuration
// ========================================
const CONFIG = {
  defaultPrompt: "TA",
  defaultTopK: 10,
  loadingText: "Searching course materials...",
  errorText: "Sorry, something went wrong. Please try again.",
};

// ========================================
// DOM Elements
// ========================================
const elements = {
  chat: document.getElementById("chat"),
  emptyState: document.getElementById("emptyState"),
  topKInput: document.getElementById("topK"),
  form: document.getElementById("chatForm"),
  input: document.getElementById("q"),
  sendBtn: document.getElementById("sendBtn"),
};

// ========================================
// State
// ========================================
const state = {
  isLoading: false,
  hasMessages: false,
};

// ========================================
// Utility Functions
// ========================================

/**
 * Escape HTML special characters to prevent XSS
 */
function escapeHtml(str) {
  const escapeMap = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  };
  return (str ?? "").replace(/[&<>"']/g, (char) => escapeMap[char]);
}

/**
 * Check if a string is an HTTP(S) URL
 */
function isHttpUrl(str) {
  return typeof str === "string" && /^https?:\/\//i.test(str);
}

/**
 * Extract filename from a file path
 */
function getFileName(path) {
  return path.split("/").pop().split("\\").pop();
}

/**
 * Scroll chat to bottom smoothly
 */
function scrollToBottom() {
  elements.chat.scrollTo({
    top: elements.chat.scrollHeight,
    behavior: "smooth",
  });
}

// ========================================
// UI Functions
// ========================================

/**
 * Hide the empty state when first message is sent
 */
function hideEmptyState() {
  if (elements.emptyState && !state.hasMessages) {
    elements.emptyState.style.display = "none";
    state.hasMessages = true;
  }
}

/**
 * Set the loading state for input controls
 */
function setLoading(loading) {
  state.isLoading = loading;
  elements.input.disabled = loading;
  elements.sendBtn.disabled = loading;

  if (!loading) {
    elements.input.focus();
  }
}

/**
 * Create the loading animation HTML
 */
function createLoadingHtml() {
  return `
    <div class="loading-wrapper">
      <div class="loading-dots">
        <span></span>
        <span></span>
        <span></span>
      </div>
      <span class="loading-text">${escapeHtml(CONFIG.loadingText)}</span>
    </div>
  `;
}

/**
 * Create a message row with avatar and bubble
 */
function createMessageRow(role, bubbleContent) {
  hideEmptyState();

  const row = document.createElement("div");
  row.className = `msg-row ${role}`;

  const avatar = document.createElement("div");
  avatar.className = `avatar ${role}`;
  avatar.textContent = role === "student" ? "Q" : "A";
  avatar.setAttribute("aria-label", role === "student" ? "Question" : "Answer");

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.innerHTML = bubbleContent;

  if (role === "student") {
    // Q: bubble left, avatar right, aligned to right
    row.appendChild(bubble);
    row.appendChild(avatar);
  } else {
    // A: avatar left, bubble right, aligned to left
    row.appendChild(avatar);
    row.appendChild(bubble);
  }

  elements.chat.appendChild(row);
  scrollToBottom();

  return { row, bubble };
}

/**
 * Create the sources panel with smooth expand/collapse
 */
function createSourcesPanel(sources) {
  if (!sources || sources.length === 0) {
    return null;
  }

  const wrap = document.createElement("div");
  wrap.className = "sources-wrap";

  // Toggle button
  const toggle = document.createElement("button");
  toggle.className = "sources-toggle";
  toggle.innerHTML = `<span class="arrow">▶</span><span>Sources (${sources.length})</span>`;
  toggle.setAttribute("aria-expanded", "false");

  // Panel content
  const panel = document.createElement("div");
  panel.className = "sources-panel";
  panel.setAttribute("aria-hidden", "true");

  const list = document.createElement("ul");
  list.className = "sources-list";

  sources.forEach((source) => {
    const li = document.createElement("li");

    if (isHttpUrl(source)) {
      const link = document.createElement("a");
      link.href = source;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = source;
      li.appendChild(link);
    } else {
      // For file paths, just show the filename
      const fileName = getFileName(source);
      const span = document.createElement("span");
      span.className = "source-file";
      span.textContent = fileName;
      li.appendChild(span);
    }

    list.appendChild(li);
  });

  panel.appendChild(list);
  wrap.appendChild(toggle);
  wrap.appendChild(panel);

  // Toggle functionality with smooth animation
  let isOpen = false;
  toggle.addEventListener("click", () => {
    isOpen = !isOpen;
    toggle.classList.toggle("open", isOpen);
    panel.classList.toggle("open", isOpen);
    toggle.setAttribute("aria-expanded", isOpen.toString());
    panel.setAttribute("aria-hidden", (!isOpen).toString());
  });

  return wrap;
}

/**
 * Render the answer and sources into the bubble
 */
function renderAnswer(bubble, answer, sources) {
  // Set the answer text
  bubble.innerHTML = escapeHtml(answer);

  // Add sources panel if available
  const sourcesPanel = createSourcesPanel(sources);
  if (sourcesPanel) {
    bubble.appendChild(sourcesPanel);
  }
}

// ========================================
// API Functions
// ========================================

/**
 * Send a question to the backend API
 */
async function sendQuestion(question) {
  const topK = Number(elements.topKInput.value) || CONFIG.defaultTopK;

  const response = await fetch("/query", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      question: question,
      prompt_name: CONFIG.defaultPrompt,
      top_k: topK,
    }),
  });

  const data = await response.json();

  // Even for error responses (429, 500), return the data so we can show the server's message
  if (!response.ok) {
    return { answer: data.answer || `Error: ${response.status}`, sources: [] };
  }

  return data;
}

// ========================================
// Main Send Handler
// ========================================

async function handleSend() {
  const question = elements.input.value.trim();
  if (!question || state.isLoading) {
    return;
  }

  // Clear input and update button state
  elements.input.value = "";
  updateSendButtonState();

  // Show user message
  createMessageRow("student", escapeHtml(question));

  // Show loading state
  const { bubble } = createMessageRow("ta", createLoadingHtml());
  setLoading(true);

  try {
    const data = await sendQuestion(question);
    renderAnswer(bubble, data.answer || "", data.sources || []);
  } catch (error) {
    console.error("Query error:", error);
    bubble.innerHTML = escapeHtml(CONFIG.errorText);
  } finally {
    setLoading(false);
    scrollToBottom();
  }
}

// ========================================
// Event Listeners
// ========================================

elements.form.addEventListener("submit", (e) => {
  e.preventDefault();
  handleSend();
});

// Handle Enter key (already handled by form submit, but good for clarity)
elements.input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey && !state.isLoading) {
    e.preventDefault();
    handleSend();
  }
});

// Toggle send button active state based on input content
function updateSendButtonState() {
  const hasContent = elements.input.value.trim().length > 0;
  elements.sendBtn.classList.toggle("active", hasContent);
}

elements.input.addEventListener("input", updateSendButtonState);

// ========================================
// Initialization
// ========================================

// Focus input on page load
elements.input.focus();
