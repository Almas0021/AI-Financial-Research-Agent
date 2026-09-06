const form = document.getElementById("research-form");
const companyInput = document.getElementById("company");
const periodInput = document.getElementById("period");
const focusInput = document.getElementById("focus");
const focusCount = document.getElementById("focus-count");
const submitButton = document.getElementById("submit");
const buttonLabel = submitButton.querySelector(".button-label");
const resultPanel = document.getElementById("result-panel");
const resultTitle = document.getElementById("result-title");
const result = document.getElementById("result");
const loadingState = document.getElementById("loading-state");
const loadingMessage = document.getElementById("loading-message");
const copyButton = document.getElementById("copy-report");
const resetButton = document.getElementById("reset-form");
const newResearchButton = document.getElementById("new-research");
const companyShell = companyInput.closest(".input-shell");

const progressMessages = [
  "Searching trusted sources…",
  "Reading filings and recent coverage…",
  "Verifying important figures…",
  "Synthesizing the final report…",
];

let progressTimer;
let currentReport = "";

function renderReport(markdown) {
  currentReport = markdown;
  if (window.marked && window.DOMPurify) {
    const rendered = window.marked.parse(markdown, { gfm: true, breaks: false });
    result.innerHTML = window.DOMPurify.sanitize(rendered);
    result.querySelectorAll("a").forEach((link) => {
      link.target = "_blank";
      link.rel = "noopener noreferrer";
    });
  } else {
    result.textContent = markdown;
  }
}

function syncInputs() {
  companyShell.classList.toggle("has-value", Boolean(companyInput.value.trim()));
  focusCount.textContent = `${focusInput.value.length} / 1000`;
}

function resetResearch() {
  form.reset();
  resultPanel.hidden = true;
  result.textContent = "";
  currentReport = "";
  syncInputs();
  companyInput.focus();
}

companyInput.addEventListener("input", syncInputs);
focusInput.addEventListener("input", syncInputs);
resetButton.addEventListener("click", resetResearch);
newResearchButton.addEventListener("click", resetResearch);

document.querySelectorAll("[data-company]").forEach((button) => {
  button.addEventListener("click", () => {
    companyInput.value = button.dataset.company;
    syncInputs();
    focusInput.focus();
  });
});

syncInputs();

function setLoading(isLoading) {
  submitButton.disabled = isLoading;
  buttonLabel.textContent = isLoading ? "Researching…" : "Start research";
  loadingState.hidden = !isLoading;
  copyButton.hidden = isLoading;

  clearInterval(progressTimer);
  if (isLoading) {
    let messageIndex = 0;
    loadingMessage.textContent = progressMessages[messageIndex];
    progressTimer = setInterval(() => {
      messageIndex = Math.min(messageIndex + 1, progressMessages.length - 1);
      loadingMessage.textContent = progressMessages[messageIndex];
    }, 6000);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!form.reportValidity()) return;

  resultPanel.hidden = false;
  resultPanel.classList.remove("error");
  result.textContent = "";
  currentReport = "";
  resultTitle.textContent = `${companyInput.value.trim()} analysis`;
  setLoading(true);
  resultPanel.scrollIntoView({ behavior: "smooth", block: "start" });

  try {
    const response = await fetch("/research", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        company: companyInput.value.trim(),
        period: periodInput.value,
        focus: focusInput.value,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Research request failed.");
    renderReport(data.report);
  } catch (error) {
    resultPanel.classList.add("error");
    resultTitle.textContent = "Research unavailable";
    result.textContent = error instanceof Error ? error.message : "An unexpected error occurred.";
  } finally {
    setLoading(false);
  }
});

copyButton.addEventListener("click", async () => {
  if (!currentReport) return;
  await navigator.clipboard.writeText(currentReport);
  copyButton.textContent = "Copied";
  setTimeout(() => { copyButton.textContent = "Copy report"; }, 1600);
});