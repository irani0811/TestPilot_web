function fillSample() {
  const projectInput = document.getElementById("project_name");
  const requirementInput = document.getElementById("requirement_text");
  if (!projectInput || !requirementInput || typeof SAMPLE_PRD === "undefined") return;
  projectInput.value = "团队任务看板 V1.0";
  requirementInput.value = SAMPLE_PRD;
  updateCharacterCount();
  requirementInput.focus();
}

function updateCharacterCount() {
  const input = document.getElementById("requirement_text");
  const counter = document.getElementById("charCount");
  if (input && counter) counter.textContent = `${input.value.length} 字`;
}

function filterCases() {
  const type = document.getElementById("typeFilter")?.value || "";
  const priority = document.getElementById("priorityFilter")?.value || "";
  const automation = document.getElementById("automationFilter")?.value || "";
  const query = (document.getElementById("caseSearch")?.value || "").trim().toLowerCase();
  let visible = 0;

  document.querySelectorAll("#caseBody .case-row").forEach((row) => {
    const matches = (!type || row.dataset.type === type)
      && (!priority || row.dataset.priority === priority)
      && (!automation || row.dataset.automation === automation)
      && (!query || row.dataset.search.toLowerCase().includes(query));
    row.hidden = !matches;
    const detail = row.nextElementSibling;
    if (detail?.classList.contains("case-detail-row")) {
      detail.hidden = true;
      row.querySelector(".expand-btn")?.setAttribute("aria-expanded", "false");
    }
    if (matches) visible += 1;
  });

  const count = document.getElementById("visibleCount");
  const empty = document.getElementById("tableEmpty");
  if (count) count.textContent = visible;
  if (empty) empty.hidden = visible !== 0;
}

function resetFilters() {
  ["typeFilter", "priorityFilter", "automationFilter", "caseSearch"].forEach((id) => {
    const element = document.getElementById(id);
    if (element) element.value = "";
  });
  filterCases();
}

function toggleCase(button) {
  const row = button.closest("tr");
  const detail = row?.nextElementSibling;
  if (!detail?.classList.contains("case-detail-row")) return;
  const willOpen = detail.hidden;
  detail.hidden = !willOpen;
  button.setAttribute("aria-expanded", String(willOpen));
}

document.addEventListener("DOMContentLoaded", () => {
  const requirementInput = document.getElementById("requirement_text");
  requirementInput?.addEventListener("input", updateCharacterCount);
  updateCharacterCount();

  const form = document.getElementById("analysisForm");
  form?.addEventListener("submit", () => {
    const button = document.getElementById("submitButton");
    if (!button) return;
    button.disabled = true;
    button.querySelector("span").textContent = "正在分析需求…";
  });

  const demoForm = document.getElementById("demoForm");
  demoForm?.addEventListener("submit", () => {
    const button = document.getElementById("demoButton");
    if (!button) return;
    button.disabled = true;
    button.textContent = "AI 正在分析示例…";
  });
});
